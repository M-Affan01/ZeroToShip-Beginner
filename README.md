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

## Project Structure

```
Beginner/
├── models/
│   └── component.py          # Component data model
├── services/
│   ├── __init__.py
│   └── auth.py               # Session management & gatekeepers
├── manual_test.py            # Demo & testing script
├── .gitignore
└── README.md
```

---

## Git Commands

```bash
git add services/auth.py services/__init__.py manual_test.py README.md
git commit -m "Phase 2 Complete: Build terminal user state tracking sessions and add state modification access gatekeepers"
git push origin main
```

---

## Notes

- **Headless Architecture** — No GUI; operates entirely via terminal/CLI
- **Session Timeout** — Sessions expire after 1 hour (3600 seconds) by default
- **Ownership Model** — Users can only modify components they own
- **No External Dependencies** — Pure Python standard library implementation

Warm regards,

Head of Team Coding and Innovation
