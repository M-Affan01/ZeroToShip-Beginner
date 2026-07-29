import json
import os
import shutil
from datetime import datetime


DEFAULT_STORAGE_FILE = "gear.json"

VALID_STATUSES = ["Available", "Borrowed", "Maintenance", "Retired"]


class StorageError(Exception):
    pass


class CorruptedDataError(StorageError):
    pass


class FileAccessError(StorageError):
    pass


class ValidationError(Exception):
    pass


def _validate_filepath(filepath):
    if filepath is None:
        raise ValidationError("Filepath cannot be None")
    if not isinstance(filepath, str):
        raise ValidationError(
            f"Filepath must be str, got {type(filepath).__name__}"
        )
    if not filepath.strip():
        raise ValidationError("Filepath cannot be empty or whitespace")
    return filepath.strip()


def _validate_component_dict(data, index=None):
    prefix = f"Item at index {index}: " if index is not None else ""

    if data is None:
        raise ValidationError(f"{prefix}Component data cannot be None")
    if not isinstance(data, dict):
        raise ValidationError(
            f"{prefix}Component data must be dict, got {type(data).__name__}"
        )

    required_keys = {"id", "name", "owner", "status"}
    missing = required_keys - set(data.keys())
    if missing:
        raise ValidationError(f"{prefix}Missing required keys: {missing}")

    if data["id"] is None:
        raise ValidationError(f"{prefix}ID cannot be None")
    if not isinstance(data["id"], (int, str)):
        raise ValidationError(
            f"{prefix}ID must be int or str, got {type(data['id']).__name__}"
        )
    if isinstance(data["id"], str) and not data["id"].strip():
        raise ValidationError(f"{prefix}ID cannot be empty string")

    if data["name"] is None:
        raise ValidationError(f"{prefix}Name cannot be None")
    if not isinstance(data["name"], str):
        raise ValidationError(
            f"{prefix}Name must be str, got {type(data['name']).__name__}"
        )
    if not data["name"].strip():
        raise ValidationError(f"{prefix}Name cannot be empty or whitespace")

    if data["owner"] is None:
        raise ValidationError(f"{prefix}Owner cannot be None")
    if not isinstance(data["owner"], str):
        raise ValidationError(
            f"{prefix}Owner must be str, got {type(data['owner']).__name__}"
        )
    if not data["owner"].strip():
        raise ValidationError(f"{prefix}Owner cannot be empty or whitespace")

    if data["status"] is None:
        raise ValidationError(f"{prefix}Status cannot be None")
    if not isinstance(data["status"], str):
        raise ValidationError(
            f"{prefix}Status must be str, got {type(data['status']).__name__}"
        )
    if data["status"] not in VALID_STATUSES:
        raise ValidationError(
            f"{prefix}Invalid status '{data['status']}'. Must be one of: {VALID_STATUSES}"
        )

    return data


def _get_backup_path(filepath):
    return filepath + ".backup"


def _create_backup(filepath):
    if os.path.exists(filepath):
        backup_path = _get_backup_path(filepath)
        shutil.copy2(filepath, backup_path)


def _restore_from_backup(filepath):
    backup_path = _get_backup_path(filepath)
    if os.path.exists(backup_path):
        shutil.copy2(backup_path, filepath)
        return True
    return False


def save_gear_data(components_dict_list, filepath=DEFAULT_STORAGE_FILE):
    _validate_filepath(filepath)

    if components_dict_list is None:
        raise ValidationError("Components list cannot be None")
    if not isinstance(components_dict_list, list):
        raise ValidationError(
            f"Components list must be list, got {type(components_dict_list).__name__}"
        )

    for i, item in enumerate(components_dict_list):
        _validate_component_dict(item, index=i)

    try:
        _create_backup(filepath)

        temp_filepath = filepath + ".tmp"

        with open(temp_filepath, "w", encoding="utf-8") as f:
            json.dump(components_dict_list, f, indent=4, ensure_ascii=False)

        if os.path.exists(filepath):
            os.remove(filepath)
        os.rename(temp_filepath, filepath)

        return True

    except PermissionError as e:
        _restore_from_backup(filepath)
        raise FileAccessError(f"Permission denied writing to '{filepath}': {e}")
    except OSError as e:
        _restore_from_backup(filepath)
        raise FileAccessError(f"OS error writing to '{filepath}': {e}")
    except TypeError as e:
        raise StorageError(f"Data serialization error: {e}")
    except Exception as e:
        _restore_from_backup(filepath)
        raise StorageError(f"Unexpected error saving data: {e}")


def load_gear_data(filepath=DEFAULT_STORAGE_FILE):
    _validate_filepath(filepath)

    if not os.path.exists(filepath):
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise CorruptedDataError(
                f"Expected list in '{filepath}', got {type(data).__name__}"
            )

        validated_data = _validate_component_dicts(data)
        return validated_data

    except json.JSONDecodeError as e:
        if _restore_from_backup(filepath):
            return load_gear_data(filepath)
        raise CorruptedDataError(f"Invalid JSON in '{filepath}': {e}")
    except PermissionError as e:
        raise FileAccessError(f"Permission denied reading '{filepath}': {e}")
    except OSError as e:
        raise FileAccessError(f"OS error reading '{filepath}': {e}")
    except CorruptedDataError:
        raise
    except Exception as e:
        raise StorageError(f"Unexpected error loading data: {e}")


def _validate_component_dicts(data):
    validated = []

    for i, item in enumerate(data):
        validated_item = _validate_component_dict(item, index=i)
        validated.append(validated_item)

    return validated


def save_single_component(component_dict, filepath=DEFAULT_STORAGE_FILE):
    _validate_filepath(filepath)
    _validate_component_dict(component_dict)

    existing = load_gear_data(filepath)

    for i, item in enumerate(existing):
        if item.get("id") == component_dict.get("id"):
            existing[i] = component_dict
            return save_gear_data(existing, filepath)

    existing.append(component_dict)
    return save_gear_data(existing, filepath)


def delete_component(component_id, filepath=DEFAULT_STORAGE_FILE):
    _validate_filepath(filepath)

    if component_id is None:
        raise ValidationError("Component ID cannot be None")
    if not isinstance(component_id, (int, str)):
        raise ValidationError(
            f"Component ID must be int or str, got {type(component_id).__name__}"
        )

    existing = load_gear_data(filepath)
    updated = [item for item in existing if item.get("id") != component_id]

    if len(updated) == len(existing):
        raise StorageError(f"Component with ID {component_id} not found in storage")

    return save_gear_data(updated, filepath)


def get_storage_info(filepath=DEFAULT_STORAGE_FILE):
    _validate_filepath(filepath)

    info = {
        "filepath": os.path.abspath(filepath),
        "exists": os.path.exists(filepath),
        "backup_exists": os.path.exists(_get_backup_path(filepath)),
    }

    if info["exists"]:
        stat = os.stat(filepath)
        info["size_bytes"] = stat.st_size
        info["last_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()

        try:
            loaded_data = load_gear_data(filepath)
            info["component_count"] = len(loaded_data)
        except (CorruptedDataError, FileAccessError, StorageError):
            info["component_count"] = -1
            info["data_status"] = "corrupted"
    else:
        info["size_bytes"] = 0
        info["last_modified"] = None
        info["component_count"] = 0

    return info
