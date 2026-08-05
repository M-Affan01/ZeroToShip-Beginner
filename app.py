import sys
import re
from models.component import Component
from services.auth import SessionManager, validate_session, can_modify_component
from services.registry_core import GearRegistry, VALID_STATUSES
from services.storage import (
    load_gear_data,
    save_gear_data,
    get_storage_info,
    DEFAULT_STORAGE_FILE,
)
from services.cli_display import (
    clear_screen,
    render_title_banner,
    render_menu,
    render_box,
    render_error,
    render_components_table,
    render_status_ledger,
    colorize_status,
    DisplayValidationError,
    ComponentDataError,
)

TRACKING_METRICS = {
    "commands_executed": 0,
    "components_added": 0,
    "components_borrowed": 0,
    "components_returned": 0,
    "components_deleted": 0,
    "searches_performed": 0,
    "errors_encountered": 0,
}

MAX_ID_LENGTH = 50
MAX_NAME_LENGTH = 100
MAX_EMAIL_LENGTH = 150
MAX_SEARCH_LENGTH = 100
ALLOWED_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


class InputValidationError(Exception):
    pass


def _track(command_key):
    TRACKING_METRICS[command_key] = TRACKING_METRICS.get(command_key, 0) + 1
    TRACKING_METRICS["commands_executed"] += 1


def _pause():
    try:
        input("\nPress Enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def _validate_non_empty(value, field_name):
    if value is None:
        raise InputValidationError(f"{field_name} cannot be None.")
    if not isinstance(value, str):
        raise InputValidationError(f"{field_name} must be text.")
    if not value.strip():
        raise InputValidationError(f"{field_name} cannot be empty or whitespace.")
    return value.strip()


def _validate_length(value, field_name, max_length):
    value = _validate_non_empty(value, field_name)
    if len(value) > max_length:
        raise InputValidationError(
            f"{field_name} cannot exceed {max_length} characters."
        )
    return value


def _validate_student_id(student_id):
    value = _validate_length(student_id, "Student ID", MAX_ID_LENGTH)
    if not ALLOWED_ID_PATTERN.match(value):
        raise InputValidationError(
            "Student ID can only contain letters, numbers, hyphens, underscores, and dots."
        )
    return value


def _validate_name(name, field_name="Name"):
    value = _validate_length(name, field_name, MAX_NAME_LENGTH)
    if any(c in value for c in '<>{}[]|\\'):
        raise InputValidationError(
            f"{field_name} contains invalid characters."
        )
    return value


def _validate_email(email):
    if email is None or not email.strip():
        return None
    value = _validate_length(email, "Email", MAX_EMAIL_LENGTH)
    if "@" not in value or "." not in value:
        raise InputValidationError("Invalid email format.")
    return value


def _validate_component_id_input(comp_id):
    value = _validate_non_empty(comp_id, "Component ID")
    if len(value) > MAX_ID_LENGTH:
        raise InputValidationError(
            f"Component ID cannot exceed {MAX_ID_LENGTH} characters."
        )
    if value.isdigit():
        return int(value)
    if not ALLOWED_ID_PATTERN.match(value):
        raise InputValidationError(
            "Component ID can only contain letters, numbers, hyphens, underscores, and dots."
        )
    return value


def _validate_status_input(status):
    value = _validate_non_empty(status, "Status")
    if value not in VALID_STATUSES:
        raise InputValidationError(
            f"Invalid status '{value}'. Must be one of: {', '.join(VALID_STATUSES)}"
        )
    return value


def _validate_search_term(term):
    value = _validate_length(term, "Search term", MAX_SEARCH_LENGTH)
    return value


def _safe_input(prompt):
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\n\n  Operation cancelled.")
        return None


def _get_dynamic_menu():
    return [
        "1. View All Components",
        "2. Add Component",
        "3. Borrow Component",
        "4. Return Component",
        "5. Mark Maintenance",
        "6. Retire Component",
        "7. Edit Component",
        "8. Delete Component",
        "9. Search Components",
        "10. Storage Status",
        "11. View Metrics",
        "12. Exit",
    ]


def _display_header():
    clear_screen()
    try:
        sys.stdout.write(render_title_banner("HARDWARE INVENTORY SYSTEM") + "\n\n")
    except Exception:
        pass
    sys.stdout.flush()


def _get_session_token(session_mgr):
    _display_header()
    try:
        sys.stdout.write(render_menu("LOGIN MENU", [
            "1. Login with Student ID",
            "2. Register New User",
            "3. Continue as Guest (View Only)",
        ]))
    except Exception:
        pass
    sys.stdout.flush()

    choice = _safe_input("\n  Select option: ")
    if choice is None:
        return None

    choice = choice.strip()

    if choice == "1":
        student_id = _safe_input("  Enter Student ID: ")
        if student_id is None:
            return _get_session_token(session_mgr)

        try:
            student_id = _validate_student_id(student_id)
        except InputValidationError as e:
            print(f"  Error: {e}")
            _pause()
            return _get_session_token(session_mgr)

        session = session_mgr.login(student_id)
        if session:
            print(f"\n  Welcome back, {session.user.name}!")
            _pause()
            return session.session_id
        else:
            print(f"\n  No account found for ID: {student_id}")
            _pause()
            return _get_session_token(session_mgr)

    elif choice == "2":
        student_id = _safe_input("  Enter new Student ID: ")
        if student_id is None:
            return _get_session_token(session_mgr)

        name = _safe_input("  Enter your name: ")
        if name is None:
            return _get_session_token(session_mgr)

        email = _safe_input("  Enter email (optional): ")
        if email is None:
            return _get_session_token(session_mgr)

        try:
            student_id = _validate_student_id(student_id)
            name = _validate_name(name, "Name")
            email = _validate_email(email) if email.strip() else None
        except InputValidationError as e:
            print(f"  Error: {e}")
            _pause()
            return _get_session_token(session_mgr)

        try:
            user = session_mgr.register_user(student_id, name, email)
            session = session_mgr.login(student_id)
            print(f"\n  Account created and logged in as: {user.name}")
            _pause()
            return session.session_id
        except Exception as e:
            print(f"\n  Registration failed: {e}")
            _pause()
            return _get_session_token(session_mgr)

    elif choice == "3":
        print("\n  Continuing as guest (view only)...")
        _pause()
        return None

    else:
        print("  Invalid option. Please select 1, 2, or 3.")
        _pause()
        return _get_session_token(session_mgr)


def _view_all_components(registry):
    _track("commands_executed")
    _display_header()
    try:
        components = registry.get_all_components()
        if not components:
            sys.stdout.write(render_box("No components in inventory.") + "\n")
        else:
            dict_list = [c.to_dict() for c in components]
            sys.stdout.write(render_components_table(dict_list) + "\n")
            sys.stdout.write("\n" + render_status_ledger(dict_list) + "\n")
    except Exception as e:
        _track("errors_encountered")
        sys.stdout.write(render_error(f"Failed to load components: {e}") + "\n")
    sys.stdout.flush()
    _pause()


def _add_component(registry, session_mgr, session_id):
    _display_header()
    try:
        sys.stdout.write(render_title_banner("ADD NEW COMPONENT") + "\n\n")
    except Exception:
        pass
    sys.stdout.flush()

    if not session_id:
        sys.stdout.write(render_error("You must be logged in to add components.") + "\n")
        sys.stdout.flush()
        _pause()
        return

    try:
        validate_session(session_mgr, session_id)
    except PermissionError as e:
        sys.stdout.write(render_error(str(e)) + "\n")
        sys.stdout.flush()
        _pause()
        return

    comp_id = _safe_input("  Component ID (int or str): ")
    if comp_id is None:
        return

    name = _safe_input("  Component Name: ")
    if name is None:
        return

    owner = _safe_input("  Owner Name: ")
    if owner is None:
        return

    status = _safe_input(f"  Status {VALID_STATUSES} (default: Available): ")
    if status is None:
        return

    try:
        comp_id = _validate_component_id_input(comp_id)
        name = _validate_name(name, "Component Name")
        owner = _validate_name(owner, "Owner Name")
        if status.strip():
            status = _validate_status_input(status)
        else:
            status = "Available"
    except InputValidationError as e:
        print(f"\n  Validation Error: {e}")
        _pause()
        return

    try:
        component = Component(comp_id, name, owner, status)
        registry.add_component(component)
        _track("components_added")
        print(f"\n  Component '{name}' added successfully!")
    except Exception as e:
        _track("errors_encountered")
        sys.stdout.write(render_error(f"Failed to add component: {e}") + "\n")
    sys.stdout.flush()
    _pause()


def _borrow_component(registry, session_mgr, session_id):
    _display_header()
    try:
        sys.stdout.write(render_title_banner("BORROW COMPONENT") + "\n\n")
    except Exception:
        pass
    sys.stdout.flush()

    if not session_id:
        sys.stdout.write(render_error("You must be logged in to borrow components.") + "\n")
        sys.stdout.flush()
        _pause()
        return

    try:
        validate_session(session_mgr, session_id)
    except PermissionError as e:
        sys.stdout.write(render_error(str(e)) + "\n")
        sys.stdout.flush()
        _pause()
        return

    components = registry.get_all_components()
    available = [c for c in components if c.status == "Available"]
    if not available:
        sys.stdout.write(render_box("No available components to borrow.") + "\n")
        sys.stdout.flush()
        _pause()
        return

    dict_list = [c.to_dict() for c in available]
    sys.stdout.write(render_components_table(dict_list) + "\n")
    sys.stdout.flush()

    comp_id = _safe_input("\n  Enter Component ID to borrow: ")
    if comp_id is None:
        return

    try:
        comp_id = _validate_component_id_input(comp_id)
    except InputValidationError as e:
        print(f"  Error: {e}")
        _pause()
        return

    try:
        component = registry.get_component(comp_id)

        if not can_modify_component(session_mgr, session_id, component):
            sys.stdout.write(render_error("You can only borrow components you own.") + "\n")
            sys.stdout.flush()
            _pause()
            return

        registry.borrow_component(comp_id)
        _track("components_borrowed")
        print(f"\n  '{component.name}' is now Borrowed!")
    except Exception as e:
        _track("errors_encountered")
        sys.stdout.write(render_error(f"Failed to borrow component: {e}") + "\n")
    sys.stdout.flush()
    _pause()


def _return_component(registry, session_mgr, session_id):
    _display_header()
    try:
        sys.stdout.write(render_title_banner("RETURN COMPONENT") + "\n\n")
    except Exception:
        pass
    sys.stdout.flush()

    if not session_id:
        sys.stdout.write(render_error("You must be logged in to return components.") + "\n")
        sys.stdout.flush()
        _pause()
        return

    try:
        validate_session(session_mgr, session_id)
    except PermissionError as e:
        sys.stdout.write(render_error(str(e)) + "\n")
        sys.stdout.flush()
        _pause()
        return

    components = registry.get_all_components()
    borrowed = [c for c in components if c.status == "Borrowed"]
    if not borrowed:
        sys.stdout.write(render_box("No borrowed components to return.") + "\n")
        sys.stdout.flush()
        _pause()
        return

    dict_list = [c.to_dict() for c in borrowed]
    sys.stdout.write(render_components_table(dict_list) + "\n")
    sys.stdout.flush()

    comp_id = _safe_input("\n  Enter Component ID to return: ")
    if comp_id is None:
        return

    try:
        comp_id = _validate_component_id_input(comp_id)
    except InputValidationError as e:
        print(f"  Error: {e}")
        _pause()
        return

    try:
        component = registry.get_component(comp_id)

        if not can_modify_component(session_mgr, session_id, component):
            sys.stdout.write(render_error("You can only return components you own.") + "\n")
            sys.stdout.flush()
            _pause()
            return

        registry.return_component(comp_id)
        _track("components_returned")
        print(f"\n  '{component.name}' is now Available!")
    except Exception as e:
        _track("errors_encountered")
        sys.stdout.write(render_error(f"Failed to return component: {e}") + "\n")
    sys.stdout.flush()
    _pause()


def _mark_maintenance(registry, session_mgr, session_id):
    _display_header()
    try:
        sys.stdout.write(render_title_banner("MARK AS MAINTENANCE") + "\n\n")
    except Exception:
        pass
    sys.stdout.flush()

    if not session_id:
        sys.stdout.write(render_error("You must be logged in.") + "\n")
        sys.stdout.flush()
        _pause()
        return

    try:
        validate_session(session_mgr, session_id)
    except PermissionError as e:
        sys.stdout.write(render_error(str(e)) + "\n")
        sys.stdout.flush()
        _pause()
        return

    components = registry.get_all_components()
    actionable = [c for c in components if c.status in ("Available", "Borrowed")]
    if not actionable:
        sys.stdout.write(render_box("No components can be marked for maintenance.") + "\n")
        sys.stdout.flush()
        _pause()
        return

    dict_list = [c.to_dict() for c in actionable]
    sys.stdout.write(render_components_table(dict_list) + "\n")
    sys.stdout.flush()

    comp_id = _safe_input("\n  Enter Component ID: ")
    if comp_id is None:
        return

    try:
        comp_id = _validate_component_id_input(comp_id)
    except InputValidationError as e:
        print(f"  Error: {e}")
        _pause()
        return

    try:
        component = registry.get_component(comp_id)

        if not can_modify_component(session_mgr, session_id, component):
            sys.stdout.write(render_error("You can only modify components you own.") + "\n")
            sys.stdout.flush()
            _pause()
            return

        registry.mark_maintenance(comp_id)
        print(f"\n  '{component.name}' is now under Maintenance!")
    except Exception as e:
        _track("errors_encountered")
        sys.stdout.write(render_error(f"Failed to mark maintenance: {e}") + "\n")
    sys.stdout.flush()
    _pause()


def _retire_component(registry, session_mgr, session_id):
    _display_header()
    try:
        sys.stdout.write(render_title_banner("RETIRE COMPONENT") + "\n\n")
    except Exception:
        pass
    sys.stdout.flush()

    if not session_id:
        sys.stdout.write(render_error("You must be logged in.") + "\n")
        sys.stdout.flush()
        _pause()
        return

    try:
        validate_session(session_mgr, session_id)
    except PermissionError as e:
        sys.stdout.write(render_error(str(e)) + "\n")
        sys.stdout.flush()
        _pause()
        return

    components = registry.get_all_components()
    actionable = [c for c in components if c.status != "Retired"]
    if not actionable:
        sys.stdout.write(render_box("No components available to retire.") + "\n")
        sys.stdout.flush()
        _pause()
        return

    dict_list = [c.to_dict() for c in actionable]
    sys.stdout.write(render_components_table(dict_list) + "\n")
    sys.stdout.flush()

    comp_id = _safe_input("\n  Enter Component ID: ")
    if comp_id is None:
        return

    try:
        comp_id = _validate_component_id_input(comp_id)
    except InputValidationError as e:
        print(f"  Error: {e}")
        _pause()
        return

    try:
        component = registry.get_component(comp_id)

        if not can_modify_component(session_mgr, session_id, component):
            sys.stdout.write(render_error("You can only modify components you own.") + "\n")
            sys.stdout.flush()
            _pause()
            return

        confirm = _safe_input(
            f"  Are you sure you want to retire '{component.name}'? (y/n): "
        )
        if confirm is None or confirm.strip().lower() != "y":
            print("  Retirement cancelled.")
            _pause()
            return

        registry.retire_component(comp_id)
        print(f"\n  '{component.name}' has been Retired.")
    except Exception as e:
        _track("errors_encountered")
        sys.stdout.write(render_error(f"Failed to retire component: {e}") + "\n")
    sys.stdout.flush()
    _pause()


def _edit_component(registry, session_mgr, session_id):
    _display_header()
    try:
        sys.stdout.write(render_title_banner("EDIT COMPONENT") + "\n\n")
    except Exception:
        pass
    sys.stdout.flush()

    if not session_id:
        sys.stdout.write(render_error("You must be logged in to edit components.") + "\n")
        sys.stdout.flush()
        _pause()
        return

    try:
        validate_session(session_mgr, session_id)
    except PermissionError as e:
        sys.stdout.write(render_error(str(e)) + "\n")
        sys.stdout.flush()
        _pause()
        return

    components = registry.get_all_components()
    if not components:
        sys.stdout.write(render_box("No components in inventory.") + "\n")
        sys.stdout.flush()
        _pause()
        return

    dict_list = [c.to_dict() for c in components]
    sys.stdout.write(render_components_table(dict_list) + "\n")
    sys.stdout.flush()

    comp_id = _safe_input("\n  Enter Component ID to edit: ")
    if comp_id is None:
        return

    try:
        comp_id = _validate_component_id_input(comp_id)
    except InputValidationError as e:
        print(f"  Error: {e}")
        _pause()
        return

    try:
        component = registry.get_component(comp_id)

        if not can_modify_component(session_mgr, session_id, component):
            sys.stdout.write(render_error("You can only edit components you own.") + "\n")
            sys.stdout.flush()
            _pause()
            return

        print(f"\n  Current Name: {component.name}")
        print(f"  Current Owner: {component.owner}")
        print(f"  Current Status: {component.status}")
        print("\n  (Press Enter to keep current value)")

        new_name = _safe_input(f"  New Name [{component.name}]: ")
        if new_name is None:
            return

        new_owner = _safe_input(f"  New Owner [{component.owner}]: ")
        if new_owner is None:
            return

        if new_name.strip():
            try:
                new_name = _validate_name(new_name, "Component Name")
            except InputValidationError as e:
                print(f"  Error: {e}")
                _pause()
                return
        else:
            new_name = None

        if new_owner.strip():
            try:
                new_owner = _validate_name(new_owner, "Owner Name")
            except InputValidationError as e:
                print(f"  Error: {e}")
                _pause()
                return
        else:
            new_owner = None

        registry.update_component(comp_id, name=new_name, owner=new_owner)
        print(f"\n  Component updated successfully!")
    except Exception as e:
        _track("errors_encountered")
        sys.stdout.write(render_error(f"Failed to edit component: {e}") + "\n")
    sys.stdout.flush()
    _pause()


def _delete_component(registry, session_mgr, session_id):
    _display_header()
    try:
        sys.stdout.write(render_title_banner("DELETE COMPONENT") + "\n\n")
    except Exception:
        pass
    sys.stdout.flush()

    if not session_id:
        sys.stdout.write(render_error("You must be logged in to delete components.") + "\n")
        sys.stdout.flush()
        _pause()
        return

    try:
        validate_session(session_mgr, session_id)
    except PermissionError as e:
        sys.stdout.write(render_error(str(e)) + "\n")
        sys.stdout.flush()
        _pause()
        return

    components = registry.get_all_components()
    if not components:
        sys.stdout.write(render_box("No components in inventory.") + "\n")
        sys.stdout.flush()
        _pause()
        return

    dict_list = [c.to_dict() for c in components]
    sys.stdout.write(render_components_table(dict_list) + "\n")
    sys.stdout.flush()

    comp_id = _safe_input("\n  Enter Component ID to delete: ")
    if comp_id is None:
        return

    try:
        comp_id = _validate_component_id_input(comp_id)
    except InputValidationError as e:
        print(f"  Error: {e}")
        _pause()
        return

    try:
        component = registry.get_component(comp_id)

        if not can_modify_component(session_mgr, session_id, component):
            sys.stdout.write(render_error("You can only delete components you own.") + "\n")
            sys.stdout.flush()
            _pause()
            return

        confirm = _safe_input(
            f"  Are you sure you want to delete '{component.name}'? (y/n): "
        )
        if confirm is None or confirm.strip().lower() != "y":
            print("  Deletion cancelled.")
            _pause()
            return

        registry.remove_component(comp_id)
        _track("components_deleted")
        print(f"\n  '{component.name}' has been deleted.")
    except Exception as e:
        _track("errors_encountered")
        sys.stdout.write(render_error(f"Failed to delete component: {e}") + "\n")
    sys.stdout.flush()
    _pause()


def _search_components(registry):
    _track("searches_performed")
    _display_header()
    try:
        sys.stdout.write(render_title_banner("SEARCH COMPONENTS") + "\n\n")
    except Exception:
        pass
    sys.stdout.flush()

    term = _safe_input("  Enter search term: ")
    if term is None:
        return

    try:
        term = _validate_search_term(term)
    except InputValidationError as e:
        print(f"  Error: {e}")
        _pause()
        return

    try:
        results = registry.search_components(term)
        if not results:
            sys.stdout.write(render_box(f"No components found matching '{term}'.") + "\n")
        else:
            print(f"\n  Found {len(results)} result(s):")
            dict_list = [c.to_dict() for c in results]
            sys.stdout.write(render_components_table(dict_list) + "\n")
    except Exception as e:
        _track("errors_encountered")
        sys.stdout.write(render_error(f"Search failed: {e}") + "\n")
    sys.stdout.flush()
    _pause()


def _view_storage_status():
    _track("commands_executed")
    _display_header()
    try:
        sys.stdout.write(render_title_banner("STORAGE STATUS") + "\n\n")
        info = get_storage_info(DEFAULT_STORAGE_FILE)
        lines = [
            f"File Path    : {info['filepath']}",
            f"Exists       : {info['exists']}",
            f"Backup Exists: {info['backup_exists']}",
            f"Size (bytes) : {info['size_bytes']}",
            f"Last Modified: {info['last_modified'] or 'N/A'}",
            f"Components   : {info['component_count']}",
        ]
        sys.stdout.write(render_box("\n".join(lines), width=50) + "\n")
    except Exception as e:
        sys.stdout.write(render_error(f"Failed to load storage info: {e}") + "\n")
    sys.stdout.flush()
    _pause()


def _view_metrics():
    _display_header()
    try:
        sys.stdout.write(render_title_banner("EXECUTION METRICS") + "\n\n")
        lines = [
            f"Commands Executed   : {TRACKING_METRICS['commands_executed']}",
            f"Components Added    : {TRACKING_METRICS['components_added']}",
            f"Components Borrowed : {TRACKING_METRICS['components_borrowed']}",
            f"Components Returned : {TRACKING_METRICS['components_returned']}",
            f"Components Deleted  : {TRACKING_METRICS['components_deleted']}",
            f"Searches Performed  : {TRACKING_METRICS['searches_performed']}",
            f"Errors Encountered  : {TRACKING_METRICS['errors_encountered']}",
        ]
        sys.stdout.write(render_box("\n".join(lines), width=45) + "\n")
    except Exception as e:
        sys.stdout.write(render_error(f"Failed to display metrics: {e}") + "\n")
    sys.stdout.flush()
    _pause()


def _save_and_exit(registry):
    try:
        data = registry.to_dict_list()
        save_gear_data(data, DEFAULT_STORAGE_FILE)
        print("\n  Data saved successfully. Goodbye!")
    except Exception as e:
        print(f"\n  Error saving data: {e}")
    sys.exit(0)


def main():
    session_mgr = SessionManager()
    registry = GearRegistry()

    try:
        data = load_gear_data(DEFAULT_STORAGE_FILE)
        registry.load_from_dict_list(data)
        print(f"  Loaded {len(registry.get_all_components())} components from storage.")
    except Exception:
        print("  Starting with empty inventory.")

    session_id = _get_session_token(session_mgr)

    menu_options = {
        "1": _view_all_components,
        "2": _add_component,
        "3": _borrow_component,
        "4": _return_component,
        "5": _mark_maintenance,
        "6": _retire_component,
        "7": _edit_component,
        "8": _delete_component,
        "9": _search_components,
        "10": _view_storage_status,
        "11": _view_metrics,
        "12": _save_and_exit,
    }

    while True:
        _display_header()

        if session_id:
            session = session_mgr.get_session(session_id)
            if session:
                print(f"  Logged in as: {session.user.name} ({session.user.student_id})")
            else:
                session_id = None
                print("  Session expired. Continuing as guest.")
        else:
            print("  Mode: Guest (View Only)")

        try:
            sys.stdout.write(render_menu("MAIN MENU", _get_dynamic_menu()) + "\n")
        except Exception:
            pass
        sys.stdout.flush()

        choice = _safe_input("\n  Select option (1-12): ")
        if choice is None:
            _save_and_exit(registry)

        choice = choice.strip()

        if choice in menu_options:
            try:
                if choice == "12":
                    _save_and_exit(registry)
                elif choice == "1":
                    _view_all_components(registry)
                elif choice == "2":
                    _add_component(registry, session_mgr, session_id)
                elif choice == "3":
                    _borrow_component(registry, session_mgr, session_id)
                elif choice == "4":
                    _return_component(registry, session_mgr, session_id)
                elif choice == "5":
                    _mark_maintenance(registry, session_mgr, session_id)
                elif choice == "6":
                    _retire_component(registry, session_mgr, session_id)
                elif choice == "7":
                    _edit_component(registry, session_mgr, session_id)
                elif choice == "8":
                    _delete_component(registry, session_mgr, session_id)
                elif choice == "9":
                    _search_components(registry)
                elif choice == "10":
                    _view_storage_status()
                elif choice == "11":
                    _view_metrics()
            except KeyboardInterrupt:
                print("\n\n  Operation interrupted.")
                _pause()
            except Exception as e:
                _track("errors_encountered")
                _display_header()
                sys.stdout.write(render_error(f"Unexpected error: {e}") + "\n")
                sys.stdout.flush()
                _pause()
        else:
            print("  Invalid option. Please select a number from 1 to 12.")
            _pause()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Application terminated by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n  Fatal error: {e}")
        sys.exit(1)
