from fnrgbookinventory.app_shared.enums import R2EnvVar
from fnrgbookinventory.gcp_services.models_services.file_storage_models import R2Config
from fnrgbookinventory.utils.keys import get_env_value


def load_r2_config_from_env() -> R2Config:
    """
    Read R2 credentials/settings from environment variables and
    return a populated R2Config. Raises EnvironmentError if any
    required variable is missing.
    """
    required_vars = (
        R2EnvVar.ACCOUNT_ID,
        R2EnvVar.ACCESS_KEY_ID,
        R2EnvVar.SECRET_ACCESS_KEY,
        R2EnvVar.BUCKET_NAME
    )
 
    values = {var: get_env_value(var) for var in R2EnvVar}
 
    missing = [var.value for var in required_vars if not values[var]]
    if missing:
        raise EnvironmentError(f"Missing required R2 env vars: {', '.join(missing)}")
 
    return R2Config(
        account_id=values[R2EnvVar.ACCOUNT_ID],
        access_key_id=values[R2EnvVar.ACCESS_KEY_ID],
        secret_access_key=values[R2EnvVar.SECRET_ACCESS_KEY],
        bucket_name=values[R2EnvVar.BUCKET_NAME]    )