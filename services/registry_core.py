from models.component import Component


VALID_STATUSES = ["Available", "Borrowed", "Maintenance", "Retired"]

VALID_TRANSITIONS = {
    "Available": ["Borrowed", "Maintenance", "Retired"],
    "Borrowed": ["Available", "Maintenance", "Retired"],
    "Maintenance": ["Available", "Retired"],
    "Retired": []
}


class InvalidTransitionError(Exception):
    pass


class ComponentNotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


class DuplicateComponentError(Exception):
    pass


def _validate_component_id(component_id):
    if component_id is None:
        raise ValidationError("Component ID cannot be None")
    if not isinstance(component_id, (int, str)):
        raise ValidationError(
            f"Component ID must be int or str, got {type(component_id).__name__}"
        )
    if isinstance(component_id, str) and not component_id.strip():
        raise ValidationError("Component ID cannot be empty string")
    return component_id


def _validate_component_name(name):
    if name is None:
        raise ValidationError("Component name cannot be None")
    if not isinstance(name, str):
        raise ValidationError(
            f"Component name must be str, got {type(name).__name__}"
        )
    if not name.strip():
        raise ValidationError("Component name cannot be empty or whitespace")
    return name.strip()


def _validate_component_owner(owner):
    if owner is None:
        raise ValidationError("Component owner cannot be None")
    if not isinstance(owner, str):
        raise ValidationError(
            f"Component owner must be str, got {type(owner).__name__}"
        )
    if not owner.strip():
        raise ValidationError("Component owner cannot be empty or whitespace")
    return owner.strip()


def _validate_status(status):
    if status is None:
        raise ValidationError("Status cannot be None")
    if not isinstance(status, str):
        raise ValidationError(
            f"Status must be str, got {type(status).__name__}"
        )
    if status not in VALID_STATUSES:
        raise ValidationError(
            f"Invalid status '{status}'. Must be one of: {VALID_STATUSES}"
        )
    return status


def validate_component_data(data):
    if data is None:
        raise ValidationError("Component data cannot be None")
    if not isinstance(data, dict):
        raise ValidationError(
            f"Component data must be dict, got {type(data).__name__}"
        )

    required_keys = {"id", "name", "owner", "status"}
    missing = required_keys - set(data.keys())
    if missing:
        raise ValidationError(f"Component data missing required keys: {missing}")

    _validate_component_id(data["id"])
    _validate_component_name(data["name"])
    _validate_component_owner(data["owner"])
    _validate_status(data["status"])

    return data


class GearRegistry:
    def __init__(self):
        self._components = {}

    def add_component(self, component):
        if component is None:
            raise ValidationError("Component cannot be None")
        if not isinstance(component, Component):
            raise ValidationError(
                f"Expected Component instance, got {type(component).__name__}"
            )

        _validate_component_id(component.id)
        _validate_component_name(component.name)
        _validate_component_owner(component.owner)
        _validate_status(component.status)

        if component.id in self._components:
            raise DuplicateComponentError(
                f"Component with ID {component.id} already exists"
            )

        self._components[component.id] = component

    def remove_component(self, component_id):
        _validate_component_id(component_id)
        if component_id not in self._components:
            raise ComponentNotFoundError(f"Component with ID {component_id} not found")
        del self._components[component_id]

    def get_component(self, component_id):
        _validate_component_id(component_id)
        component = self._components.get(component_id)
        if not component:
            raise ComponentNotFoundError(f"Component with ID {component_id} not found")
        return component

    def get_all_components(self):
        return list(self._components.values())

    def get_components_by_status(self, status):
        _validate_status(status)
        return [c for c in self._components.values() if c.status == status]

    def can_transition(self, component_id, new_status):
        _validate_component_id(component_id)
        if new_status not in VALID_STATUSES:
            return False
        component = self.get_component(component_id)
        allowed = VALID_TRANSITIONS.get(component.status, [])
        return new_status in allowed

    def transition_status(self, component_id, new_status):
        _validate_component_id(component_id)
        _validate_status(new_status)

        component = self.get_component(component_id)
        current = component.status
        allowed = VALID_TRANSITIONS.get(current, [])

        if new_status not in allowed:
            raise InvalidTransitionError(
                f"Cannot transition from '{current}' to '{new_status}'. "
                f"Allowed transitions: {allowed}"
            )

        component.status = new_status
        return component

    def borrow_component(self, component_id):
        return self.transition_status(component_id, "Borrowed")

    def return_component(self, component_id):
        return self.transition_status(component_id, "Available")

    def mark_maintenance(self, component_id):
        return self.transition_status(component_id, "Maintenance")

    def retire_component(self, component_id):
        return self.transition_status(component_id, "Retired")

    def to_dict_list(self):
        return [c.to_dict() for c in self._components.values()]

    def load_from_dict_list(self, dict_list):
        if dict_list is None:
            raise ValidationError("Dictionary list cannot be None")
        if not isinstance(dict_list, list):
            raise ValidationError(
                f"Expected list, got {type(dict_list).__name__}"
            )

        self._components.clear()

        for i, data in enumerate(dict_list):
            try:
                validated_data = validate_component_data(data)
                component = Component.from_dict(validated_data)
                self._components[component.id] = component
            except ValidationError as e:
                raise ValidationError(f"Invalid component at index {i}: {e}")
            except Exception as e:
                raise ValidationError(
                    f"Error loading component at index {i}: {e}"
                )

    def update_component(self, component_id, name=None, owner=None):
        component = self.get_component(component_id)

        if name is not None:
            _validate_component_name(name)
            component.name = name

        if owner is not None:
            _validate_component_owner(owner)
            component.owner = owner

        return component

    def search_components(self, search_term):
        if search_term is None:
            raise ValidationError("Search term cannot be None")
        if not isinstance(search_term, str):
            raise ValidationError(
                f"Search term must be str, got {type(search_term).__name__}"
            )
        if not search_term.strip():
            raise ValidationError("Search term cannot be empty or whitespace")

        term = search_term.strip().lower()
        results = []
        for comp in self._components.values():
            if (term in comp.name.lower() or term in comp.owner.lower()):
                results.append(comp)
        return results
