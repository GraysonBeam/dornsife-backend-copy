import os


def fetch_environment_variable(variable_name: str) -> str:
    value = os.getenv(variable_name)
    if not value:
        raise ValueError(f"Environment variable {variable_name} is not set")
    return value


def fetch_bool_environment_variable(variable_name: str) -> bool:
    value = fetch_environment_variable(variable_name).strip().lower()

    if value == "true":
        return True
    if value == "false":
        return False

    raise ValueError(f"Environment variable {variable_name} must be a boolean")
