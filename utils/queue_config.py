from fnrgbookinventory.app_shared.enums import PubSubEnvVar
from fnrgbookinventory.gcp_services.models_services.queue_storage import PubSubConfig
from fnrgbookinventory.utils.keys import get_env_value


def load_pubsub_config_from_env() -> PubSubConfig:
    """
    Read Pub/Sub settings from environment variables and return a
    populated PubSubConfig. Raises EnvironmentError if GCP_PROJECT_ID
    is missing.
    """
    project_id = get_env_value(PubSubEnvVar.PROJECT_ID, required=True)
    credentials_path = get_env_value(PubSubEnvVar.CREDENTIALS_PATH)

    return PubSubConfig(project_id=project_id, credentials_path=credentials_path)