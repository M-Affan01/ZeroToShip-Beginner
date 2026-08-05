import os
import re
import sys


# ---------------------------------------------------------------------------
# ANSI escape color constants
# ---------------------------------------------------------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
REVERSE = "\033[7m"

BRIGHT_GREEN = "\033[92m"
BRIGHT_RED = "\033[91m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_WHITE = "\033[97m"
GRAY = "\033[90m"

_ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------
class DisplayError(Exception):
    """Base exception for the terminal display layer."""


class DisplayValidationError(DisplayError, ValueError):
    """Raised when display input fails validation checks."""


class ComponentDataError(DisplayValidationError):
    """Raised when a component record is malformed or incomplete."""


class RenderError(DisplayError):
    """Raised when a screen fails to render from valid-looking input."""


# ---------------------------------------------------------------------------
# Status color mapping
# ---------------------------------------------------------------------------
STATUS_STYLES = {
    "Available": BRIGHT_GREEN,
    "Borrowed": BRIGHT_RED,
    "Maintenance": BRIGHT_YELLOW,
    "Retired": GRAY,
}


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------
def _validate_text(text, name="Text"):
    if text is None:
        raise DisplayValidationError(f"{name} cannot be None")
    if not isinstance(text, str):
        raise DisplayValidationError(
            f"{name} must be str, got {type(text).__name__}"
        )
    if not text.strip():
        raise DisplayValidationError(f"{name} cannot be empty or whitespace")
    return text.strip()


def _validate_status(status):
    return _validate_text(status, "Status")


def _validate_padding(padding):
    if isinstance(padding, bool) or not isinstance(padding, int):
        raise DisplayValidationError(
            f"Padding must be int, got {type(padding).__name__}"
        )
    if padding < 0:
        raise DisplayValidationError(f"Padding cannot be negative, got {padding}")
    return padding


def _validate_bool_flag(value, name):
    if not isinstance(value, bool):
        raise DisplayValidationError(
            f"{name} must be bool, got {type(value).__name__}"
        )
    return value


def _validate_headers(headers):
    if headers is None:
        raise DisplayValidationError("Headers cannot be None")
    if not isinstance(headers, list):
        raise DisplayValidationError(
            f"Headers must be list, got {type(headers).__name__}"
        )
    if not headers:
        raise DisplayValidationError("Headers cannot be empty")
    for h in headers:
        _validate_text(h, "Header")
    return headers


def _validate_rows(rows):
    if rows is None:
        raise DisplayValidationError("Rows cannot be None")
    if not isinstance(rows, list):
        raise DisplayValidationError(
            f"Rows must be list, got {type(rows).__name__}"
        )
    for i, row in enumerate(rows):
        if not isinstance(row, list):
            raise DisplayValidationError(
                f"Row at index {i} must be list, got {type(row).__name__}"
            )
    return rows


def _validate_options(options):
    if options is None:
        raise DisplayValidationError("Options cannot be None")
    if not isinstance(options, list):
        raise DisplayValidationError(
            f"Options must be list, got {type(options).__name__}"
        )
    if not options:
        raise DisplayValidationError("Options cannot be empty")
    for i, opt in enumerate(options):
        _validate_text(opt, f"Option at index {i}")
    return options


def _validate_widths(widths):
    if widths is None:
        raise DisplayValidationError("Widths cannot be None")
    if not isinstance(widths, list):
        raise DisplayValidationError(
            f"Widths must be list, got {type(widths).__name__}"
        )
    if not widths:
        raise DisplayValidationError("Widths cannot be empty")
    for i, w in enumerate(widths):
        if isinstance(w, bool) or not isinstance(w, int):
            raise DisplayValidationError(
                f"Width at index {i} must be int, got {type(w).__name__}"
            )
        if w < 0:
            raise DisplayValidationError(
                f"Width at index {i} cannot be negative, got {w}"
            )
    return widths


def _validate_component_dict(comp, index=None):
    prefix = f"Component at index {index}: " if index is not None else ""
    if comp is None:
        raise ComponentDataError(f"{prefix}Component cannot be None")
    if not isinstance(comp, dict):
        raise ComponentDataError(
            f"{prefix}Component must be dict, got {type(comp).__name__}"
        )

    required = {"id", "name", "owner", "status"}
    missing = required - set(comp.keys())
    if missing:
        raise ComponentDataError(
            f"{prefix}Missing required keys: {sorted(missing)}"
        )

    if comp["id"] is None:
        raise ComponentDataError(f"{prefix}ID cannot be None")
    if isinstance(comp["id"], str) and not comp["id"].strip():
        raise ComponentDataError(f"{prefix}ID cannot be empty string")

    _validate_text(comp["name"], f"{prefix}Name")
    _validate_text(comp["owner"], f"{prefix}Owner")
    _validate_text(comp["status"], f"{prefix}Status")
    return comp


def _validate_components(components):
    if components is None:
        raise DisplayValidationError("Components cannot be None")
    if not isinstance(components, list):
        raise DisplayValidationError(
            f"Components must be list, got {type(components).__name__}"
        )
    for i, comp in enumerate(components):
        _validate_component_dict(comp, index=i)
    return components


# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------
def clear_screen():
    """Clear the console screen using the platform-appropriate command.

    OS-level failures are tolerated silently so a headless environment
    never crashes on this call.
    """
    try:
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")
    except OSError:
        pass


def _visible_len(text):
    """Return the printable width of text with ANSI escapes stripped."""
    if text is None:
        return 0
    return len(_ANSI_PATTERN.sub("", str(text)))


def _ljust_ansi(text, width):
    """Left-justify text to a width measured without ANSI escape codes."""
    text = str(text)
    padding = max(0, width - _visible_len(text))
    return text + (" " * padding)


# ---------------------------------------------------------------------------
# ASCII border / grid primitives
# ---------------------------------------------------------------------------
def _draw_border(widths, dash="-", left="+", mid="+", right="+", padding=1):
    _validate_widths(widths)
    padding = _validate_padding(padding)
    segments = [dash * (w + 2 * padding) for w in widths]
    return left + mid.join(segments) + right


def _draw_row(cells, widths, padding=1):
    _validate_widths(widths)
    padding = _validate_padding(padding)
    if len(cells) != len(widths):
        raise DisplayValidationError(
            f"Row has {len(cells)} cells, expected {len(widths)}"
        )

    parts = [
        (" " * padding) + _ljust_ansi(cell, w) + (" " * padding)
        for cell, w in zip(cells, widths)
    ]
    return "|" + "|".join(parts) + "|"


def render_table(headers, rows, padding=1):
    """Draw an ASCII grid table using +, - and | markers.

    Column widths are derived from the widest header/cell so every line
    stays perfectly aligned.

    Raises:
        DisplayValidationError: if headers, rows, or padding are invalid.
    """
    headers = _validate_headers(headers)
    rows = _validate_rows(rows)
    padding = _validate_padding(padding)

    for i, row in enumerate(rows):
        if len(row) != len(headers):
            raise DisplayValidationError(
                f"Row at index {i} has {len(row)} cells, "
                f"expected {len(headers)}"
            )

    widths = [_visible_len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], _visible_len(cell))

    lines = []
    lines.append(_draw_border(widths, padding=padding))
    lines.append(_draw_row(headers, widths, padding=padding))
    lines.append(_draw_border(widths, padding=padding))
    for row in rows:
        lines.append(_draw_row(row, widths, padding=padding))
    lines.append(_draw_border(widths, padding=padding))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Menu rendering
# ---------------------------------------------------------------------------
def render_menu(title, options, padding=2):
    """Draw a bordered vertical menu centered around a title string.

    Raises:
        DisplayValidationError: if title, options, or padding are invalid.
    """
    title = _validate_text(title, "Title")
    options = _validate_options(options)
    padding = _validate_padding(padding)

    width = max(_visible_len(title), *(_visible_len(o) for o in options))

    lines = []
    lines.append(_draw_border([width], padding=padding))
    lines.append(_draw_row([title], [width], padding=padding))
    lines.append(_draw_border([width], padding=padding))
    for opt in options:
        lines.append(_draw_row([opt], [width], padding=padding))
    lines.append(_draw_border([width], padding=padding))
    return "\n".join(lines)


def render_title_banner(text, padding=2):
    """Draw a highlighted title banner bounded by an ASCII frame.

    Raises:
        DisplayValidationError: if text or padding are invalid.
    """
    text = _validate_text(text, "Text")
    padding = _validate_padding(padding)

    width = _visible_len(text)
    banner = [BOLD, BRIGHT_CYAN, text, RESET]
    return (
        _draw_border([width], padding=padding)
        + "\n"
        + _draw_row(["" .join(banner)], [width], padding=padding)
        + "\n"
        + _draw_border([width], padding=padding)
    )


def render_box(text, width=60, padding=2):
    """Draw a bordered text box that word-wraps long content.

    Raises:
        DisplayValidationError: if text, width, or padding are invalid.
    """
    text = _validate_text(text, "Text")
    padding = _validate_padding(padding)
    if isinstance(width, bool) or not isinstance(width, int):
        raise DisplayValidationError(
            f"Width must be int, got {type(width).__name__}"
        )
    if width < 10:
        raise DisplayValidationError(f"Width must be >= 10, got {width}")

    body_width = width
    words = str(text).split()
    wrapped = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if _visible_len(candidate) <= body_width:
            current = candidate
        else:
            if current:
                wrapped.append(current)
            current = word
    if current:
        wrapped.append(current)

    lines = [_draw_border([width], padding=padding)]
    for line in wrapped:
        lines.append(_draw_row([line], [width], padding=padding))
    lines.append(_draw_border([width], padding=padding))
    return "\n".join(lines)


def render_error(message):
    """Render a bordered error frame for a failed display operation."""
    text = message if isinstance(message, str) else str(message)
    return render_box(f"ERROR: {text}", width=60)


# ---------------------------------------------------------------------------
# Status tag highlighting
# ---------------------------------------------------------------------------
def colorize_status(status):
    """Return a color-wrapped [status] tag.

    [Available] is printed with bright green escape characters and
    [Borrowed] is wrapped in a red highlight so the two states stand out.

    Raises:
        DisplayValidationError: if status is missing, not str, or blank.
    """
    status = _validate_status(status)
    color = STATUS_STYLES.get(status, BRIGHT_WHITE)
    return f"{color}[{status}]{RESET}"


def render_status_ledger(components, summary=True):
    """Loop over components printing color-coded status tags.

    Each row reuses the colored [Available]/[Borrowed] highlighters.

    Raises:
        DisplayValidationError: if components are malformed or empty.
    """
    if components is None:
        raise DisplayValidationError("Components list cannot be None")
    items = _validate_components(components)
    summary = _validate_bool_flag(summary, "Summary")
    widths = [3, 18, 16, 16]

    lines = []
    lines.append(render_title_banner("STATUS LEDGER"))
    lines.append("")
    lines.append(_draw_border(widths))
    lines.append(_draw_row(["ID", "Name", "Owner", "Status"], widths))
    lines.append(_draw_border(widths))
    for comp in items:
        status_tag = colorize_status(comp["status"])
        lines.append(
            _draw_row([comp["id"], comp["name"], comp["owner"], status_tag], widths)
        )
    lines.append(_draw_border(widths))

    if summary:
        available = sum(1 for c in items if c["status"] == "Available")
        borrowed = sum(1 for c in items if c["status"] == "Borrowed")
        summary_widths = [18, 18, 18, 18]
        lines.append("")
        lines.append(_draw_border(summary_widths))
        lines.append(
            _draw_row(
                [
                    colorize_status("Available"),
                    f"Count: {available}",
                    colorize_status("Borrowed"),
                    f"Count: {borrowed}",
                ],
                summary_widths,
            )
        )
        lines.append(_draw_border(summary_widths))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# High-level static screens
# ---------------------------------------------------------------------------
def render_components_table(components):
    """Render a full grid table of the component inventory.

    Raises:
        DisplayValidationError: if components are malformed or empty.
    """
    if components is None:
        raise DisplayValidationError("Components list cannot be None")
    items = _validate_components(components)
    headers = ["ID", "Name", "Owner", "Status"]
    rows = [
        [comp["id"], comp["name"], comp["owner"], colorize_status(comp["status"])]
        for comp in items
    ]
    return render_table(headers, rows)


def render_dashboard(components, menu_options):
    """Compose the full static terminal dashboard from dynamic data.

    Raises:
        RenderError: if any sub-screen fails to build.
    """
    try:
        lines = []
        lines.append(render_title_banner("HARDWARE INVENTORY SYSTEM"))
        lines.append("")
        lines.append(render_menu("MAIN MENU", menu_options))
        lines.append("")
        lines.append(render_components_table(components))
        return "\n".join(lines)
    except DisplayError as e:
        raise RenderError(f"Failed to render dashboard: {e}") from e


def show_home_screen(components, menu_options):
    """Clear the console and display the complete home screen with dynamic data.

    Rendering failures are captured and shown inside an error frame rather
    than crashing the terminal session.
    """
    clear_screen()
    try:
        sys.stdout.write(render_dashboard(components, menu_options) + "\n")
    except DisplayError as e:
        sys.stdout.write(render_error(str(e)) + "\n")
    except Exception as e:
        sys.stdout.write(render_error(f"Unexpected rendering failure: {e}") + "\n")
    finally:
        sys.stdout.flush()


if __name__ == "__main__":
    demo_components = [
        {"id": 1, "name": "Arduino Uno", "owner": "Demo User", "status": "Available"},
        {"id": 2, "name": "Raspberry Pi 4", "owner": "Demo User", "status": "Borrowed"},
    ]
    demo_menu = ["1. View All Components", "2. Exit"]
    show_home_screen(demo_components, demo_menu)
