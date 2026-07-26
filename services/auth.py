import time
import hashlib
import secrets


class User:
    def __init__(self, student_id, name, email=None):
        self.student_id = student_id
        self.name = name
        self.email = email

    def to_dict(self):
        return {
            "student_id": self.student_id,
            "name": self.name,
            "email": self.email
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["student_id"],
            data["name"],
            data.get("email")
        )

    def __str__(self):
        return (f"Student ID: {self.student_id}, "
                f"Name: {self.name}, "
                f"Email: {self.email}")


class Session:
    def __init__(self, session_id, user, created_at=None):
        self.session_id = session_id
        self.user = user
        self.created_at = created_at or time.time()

    def is_valid(self, timeout=3600):
        return (time.time() - self.created_at) < timeout

    def __str__(self):
        return (f"Session ID: {self.session_id}, "
                f"User: {self.user.name}, "
                f"Created: {self.created_at}")


class SessionManager:
    def __init__(self):
        self._active_sessions = {}
        self._users = {}

    def register_user(self, student_id, name, email=None):
        user = User(student_id, name, email)
        self._users[student_id] = user
        return user

    def get_user(self, student_id):
        return self._users.get(student_id)

    def login(self, student_id):
        user = self._users.get(student_id)
        if not user:
            return None

        session_id = secrets.token_hex(16)
        session = Session(session_id, user)
        self._active_sessions[session_id] = session
        return session

    def logout(self, session_id):
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
            return True
        return False

    def get_session(self, session_id):
        session = self._active_sessions.get(session_id)
        if session and session.is_valid():
            return session
        elif session:
            del self._active_sessions[session_id]
        return None

    def is_logged_in(self, session_id):
        return self.get_session(session_id) is not None

    def get_active_sessions(self):
        return list(self._active_sessions.values())


def require_session(session_manager):
    def decorator(func):
        def wrapper(session_id, *args, **kwargs):
            session = session_manager.get_session(session_id)
            if not session:
                raise PermissionError("No active session. Please login first.")
            return func(session_id, *args, **kwargs)
        return wrapper
    return decorator


def validate_session(session_manager, session_id):
    session = session_manager.get_session(session_id)
    if not session:
        raise PermissionError("Invalid or expired session. Please login again.")
    return session


def can_modify_component(session_manager, session_id, component):
    session = session_manager.get_session(session_id)
    if not session:
        return False
    return session.user.student_id == component.owner or session.user.name == component.owner
