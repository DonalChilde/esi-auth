"""Utility to create shell-safe environment variable names."""


def make_safe_env_name(name: str) -> str:
    """Convert a string into a shell-safe environment variable name.

    The transformation performs the following steps:
    - Strips leading and trailing whitespace
    - Converts all characters to uppercase
    - Replaces any character not in [A-Z0-9_] with an underscore (_)

    Note:
    - Multiple adjacent disallowed characters may produce consecutive underscores.
    - This function does not enforce a leading alphabetic character; the result may start with a digit.

    Args:
        name: The input string to sanitize.

    Returns:
        A sanitized name containing only uppercase letters, digits, and underscores.

    Examples:
        >>> make_safe_for_env(" db-host ")
        'DB_HOST'
        >>> make_safe_for_env("path.to.value")
        'PATH_TO_VALUE'
        >>> make_safe_for_env("User ID #42")
        'USER_ID__42'
    """
    env_var_name = name.strip().upper()
    for char in env_var_name:
        if char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_":
            env_var_name = env_var_name.replace(char, "_")
    return env_var_name
