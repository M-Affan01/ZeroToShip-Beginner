from models.component import Component
from services.auth import SessionManager, validate_session, can_modify_component
from services.cli_display import (
    render_menu,
    render_components_table,
    render_status_ledger,
    colorize_status,
    render_error,
    DisplayValidationError,
    ComponentDataError,
)

# Create a Component object
component = Component(1, "Arduino Uno", "Muhammad Affan")

print("Original Object:")
print(component)

# Convert object to dictionary
component_dict = component.to_dict()

print("\nDictionary:")
print(component_dict)

# Convert dictionary back to object
new_component = Component.from_dict(component_dict)

print("\nObject Created from Dictionary:")
print(new_component)

# Phase 2: Authentication Demo
print("\n" + "=" * 50)
print("PHASE 2: Authentication & Session Management")
print("=" * 50)

# Initialize session manager
session_mgr = SessionManager()

# Register a user
user = session_mgr.register_user("STU001", "Muhammad Affan", "affan@example.com")
print(f"\nRegistered User: {user}")

# Login
session = session_mgr.login("STU001")
print(f"Session Created: {session.session_id[:16]}...")

# Validate session
try:
    validated = validate_session(session_mgr, session.session_id)
    print(f"Session Validated: {validated.user.name}")
except PermissionError as e:
    print(f"Error: {e}")

# Check if user can modify component
can_modify = can_modify_component(session_mgr, session.session_id, component)
print(f"Can modify component: {can_modify}")

# Logout
session_mgr.logout(session.session_id)
print("Logged out successfully")

# Try to access after logout
try:
    validate_session(session_mgr, session.session_id)
except PermissionError as e:
    print(f"Post-logout access attempt: {e}")

# Phase 4: Static Terminal Display Demo
print("\n" + "=" * 50)
print("PHASE 4: Static Terminal Display & Status Highlights")
print("=" * 50)

# Hardcoded status tags: [Available] in green, [Borrowed] in red
print(f"\nStatus Tag Highlights:")
print(f"  {colorize_status('Available')}")
print(f"  {colorize_status('Borrowed')}")
print(f"  {colorize_status('Maintenance')}")
print(f"  {colorize_status('Retired')}")

# ASCII framed menu grid
print(f"\nMain Menu:")
print(render_menu("MAIN MENU", [
    "1. View All Components",
    "2. Borrow Component",
    "3. Return Component",
    "4. Search Components",
    "5. Storage Status",
    "6. Exit",
]))

# Full grid table over hardcoded mock components
print(f"\nInventory Table:")
print(render_components_table())

# Status ledger loop with color-coded tags
print(f"\nStatus Ledger:")
print(render_status_ledger())

# Phase 4 error handling & input validation demo
print(f"\nError Handling & Input Validation:")

def demo_invalid(label, fn):
    try:
        fn()
        print(f"  {label}: NO ERROR RAISED (unexpected)")
    except (DisplayValidationError, ComponentDataError) as e:
        print(f"  {label} -> {type(e).__name__}: {e}")

demo_invalid("Empty status tag      ", lambda: colorize_status("  "))
demo_invalid("Missing component keys", lambda: render_status_ledger([{"id": 1}]))
demo_invalid("Non-dict component row", lambda: render_components_table(["not-a-dict"]))
demo_invalid("Negative padding      ", lambda: render_menu("T", ["a"], padding=-1))

# Error frames render gracefully without crashing
print(f"\nError Frame:")
print(render_error("Borrow failed: no active session. Please login first."))