from enum import Enum
import os
from typing import Optional
from dotenv import load_dotenv
load_dotenv()  

def get_env_value(
    var: Enum,
    *,
    required: bool = False,
    default: Optional[str] = None,
) -> Optional[str]:
    """
    Generic helper to read an environment variable using an Enum member
    whose `.value` is the variable's name (e.g. R2EnvVar.ACCOUNT_ID).
 
    Works for any str-valued Enum, not just R2EnvVar, so it can be reused
    for other config sources in the same codebase.
 
    Args:
        var: Enum member whose `.value` is the env var name.
        required: if True, raises EnvironmentError when the value is missing/empty.
        default: fallback value if the env var is not set.
 
    Returns:
        The env var's value, `default` if unset, or raises if `required` and missing.
    """
    value = os.environ.get(var.value, default)
    if required and not value:
        raise EnvironmentError(f"Missing required environment variable: {var.value}")
    return value