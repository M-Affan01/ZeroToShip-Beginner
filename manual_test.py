from models.component import Component
from services.auth import SessionManager, validate_session, can_modify_component

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