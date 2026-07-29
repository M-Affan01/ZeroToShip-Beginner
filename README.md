# ZeroToShip — Beginner Track

A terminal-based hardware inventory management system with session-based authentication.

## Project Overview

This project implements a **headless local validation engine and credential manager** for tracking hardware components. It provides secure session management and access control to prevent unauthorized modifications to hardware status fields.

---

## Phase 1 — Component Data Model

Defines the physical structure of hardware component objects with serialization support.

### Files
- `models/component.py` — `Component` class with `id` (int), `name` (str), `owner` (str), and `status` (defaults to "Available")
- `manual_test.py` — Demo script for instantiation and dictionary conversion

---

## Phase 2 — Authentication & Session Management

A lightweight user session log system that tracks actively logged-in terminal users and enforces access gatekeepers.

### Core Components

#### `services/auth.py`

| Class/Function | Description |
|----------------|-------------|
| `User` | Student profile model (student_id, name, email) |
| `Session` | Session token with timeout validation |
| `SessionManager` | Tracks active sessions, handles login/logout |
| `validate_session()` | Gatekeeper requiring active session |
| `can_modify_component()` | Ownership verification gatekeeper |
| `require_session` | Decorator for protecting functions |

### Key Features

**Authentication Flow:**
1. Register user → `session_mgr.register_user(student_id, name, email)`
2. Login → `session_mgr.login(student_id)` returns session token
3. Validate → `validate_session(session_mgr, session_id)` ensures active session
4. Logout → `session_mgr.logout(session_id)` destroys session

**Access Gatekeepers:**
- `validate_session()` — Raises `PermissionError` if no active session exists
- `can_modify_component()` — Returns `True` only if logged-in user owns the component
- `require_session` — Decorator that blocks function execution without valid session

### How to Run

```bash
py manual_test.py
```

**Expected Output:**
```
Original Object:
ID: 1, Name: Arduino Uno, Owner: Muhammad Affan, Status: Available

Dictionary:
{'id': 1, 'name': 'Arduino Uno', 'owner': 'Muhammad Affan', 'status': 'Available'}

Object Created from Dictionary:
ID: 1, Name: Arduino Uno, Owner: Muhammad Affan, Status: Available

==================================================
PHASE 2: Authentication & Session Management
==================================================

Registered User: Student ID: STU001, Name: Muhammad Affan, Email: affan@example.com
Session Created: 215f3f58c17a3395...
Session Validated: Muhammad Affan
Can modify component: True
Logged out successfully
Post-logout access attempt: Invalid or expired session. Please login again.
```

---

## Phase 3 — State Transitions & JSON Persistence

Operational application logic routines managing physical resource transformations and disk flat-file tracking.

### Core Components

#### `services/registry_core.py`

| Class/Function | Description |
|----------------|-------------|
| `GearRegistry` | In-memory component registry with state transition enforcement |
| `InvalidTransitionError` | Raised when a status change violates transition rules |
| `ComponentNotFoundError` | Raised when a component ID doesn't exist |
| `ValidationError` | Raised when input fails validation checks |
| `DuplicateComponentError` | Raised when adding a component with existing ID |
| `validate_component_data()` | Validates component dict has all required fields |

**State Transition Rules:**

| Current Status | Allowed Transitions |
|----------------|---------------------|
| Available | Borrowed, Maintenance, Retired |
| Borrowed | Available, Maintenance, Retired |
| Maintenance | Available, Retired |
| Retired | *(none — terminal state)* |

#### `services/storage.py`

| Class/Function | Description |
|----------------|-------------|
| `save_gear_data()` | Atomic write with backup and temp file pattern |
| `load_gear_data()` | Read with corruption detection and auto-restore |
| `save_single_component()` | Upsert a single component to storage |
| `delete_component()` | Remove a component by ID from storage |
| `get_storage_info()` | Returns file metadata and component count |
| `StorageError` | Base exception for storage failures |
| `CorruptedDataError` | Raised when JSON data is invalid or missing keys |
| `FileAccessError` | Raised for permission or OS-level file errors |
| `ValidationError` | Raised when input parameters are invalid |

### Key Features

**State Transition Enforcement:**
- Components can only transition to "Borrowed" if current status is explicitly "Available"
- All transitions validated against allowed paths before modification
- Invalid transitions raise `InvalidTransitionError` with descriptive message

**Fault-Tolerant Storage:**
- Atomic writes using temp file + rename pattern
- Automatic backup before every write operation
- Auto-restore from backup on JSON corruption
- Input validation on all save/load operations

**Input Validation:**
- Component ID: must be int or str, cannot be None/empty
- Component name/owner: must be non-empty str
- Status: must be one of the four valid statuses
- Filepath: must be non-empty str
- All functions validate inputs before execution

### How to Run

```bash
py manual_test.py
```

### Example Usage

```python
from models.component import Component
from services.registry_core import GearRegistry
from services.storage import save_gear_data, load_gear_data

# Create and register components
registry = GearRegistry()
comp1 = Component(1, "Arduino Uno", "Affan")
registry.add_component(comp1)

# Valid transition: Available → Borrowed
registry.borrow_component(1)
print(comp1.status)  # Borrowed

# Invalid transition: Borrowed → Borrowed (raises error)
registry.borrow_component(1)  # InvalidTransitionError

# Save to disk
save_gear_data(registry.to_dict_list())

# Load from disk
loaded = load_gear_data()
```

---

## Project Structure

```
Beginner/
├── models/
│   └── component.py          # Component data model
├── services/
│   ├── __init__.py
│   ├── auth.py               # Session management & gatekeepers
│   ├── registry_core.py      # State transition logic & validation
│   └── storage.py            # JSON persistence layer
├── manual_test.py            # Demo & testing script
├── .gitignore
└── README.md
```

---

## Git Commands

**Phase 2:**
```bash
git add services/auth.py services/__init__.py manual_test.py README.md
git commit -m "Phase 2 Complete: Build terminal user state tracking sessions and add state modification access gatekeepers"
git push origin main
```

**Phase 3:**
```bash
git add services/registry_core.py services/storage.py README.md
git commit -m "Phase 3 Complete: Deploy hardware state transition triggers and build fault-tolerant JSON storage pipelines"
git push origin main
```

---

## Notes

- **Headless Architecture** — No GUI; operates entirely via terminal/CLI
- **Session Timeout** — Sessions expire after 1 hour (3600 seconds) by default
- **Ownership Model** — Users can only modify components they own
- **State Enforcement** — Invalid status transitions are blocked at the registry level
- **Data Safety** — Storage layer uses atomic writes with automatic backup/restore
- **Input Validation** — All public functions validate parameters before execution
- **No External Dependencies** — Pure Python standard library implementation

Warm regards,

Head of Team Coding and Innovation
