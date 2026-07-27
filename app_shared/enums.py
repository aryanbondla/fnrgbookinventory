from enum import Enum


class R2EnvVar(str, Enum):
    """Names of the environment variables used to configure R2."""

    ACCOUNT_ID = "R2_ACCOUNT_ID"
    ACCESS_KEY_ID = "R2_ACCESS_KEY_ID"
    SECRET_ACCESS_KEY = "R2_SECRET_ACCESS_KEY"
    BUCKET_NAME = "R2_BUCKET_NAME"


class R2ClientDefaults(str, Enum):
    """Fixed values required by boto3/R2 when creating the S3 client."""

    SERVICE_NAME = "s3"
    REGION = "auto"
    SIGNATURE_VERSION = "s3v4"


class S3ErrorCode(str, Enum):
    """Error codes returned by boto3 that this service checks for."""

    NOT_FOUND = "404"
    NO_SUCH_KEY = "NoSuchKey"
    NOT_FOUND_NAME = "NotFound"

class boto3_enums(str, Enum):
    """Fixed values required by boto3/R2 when creating the S3 client."""
    END_POINT_URL = "R2_BUCKET_END_POINT_URL"


class PubSubEnvVar(str, Enum):
    """Names of the environment variables used to configure Pub/Sub."""

    PROJECT_ID = "GCP_PROJECT_ID"
    CREDENTIALS_PATH = "GOOGLE_APPLICATION_CREDENTIALS"


class AckAction(str, Enum):
    """Actions available when handling a pulled message."""

    ACK = "ack"
    NACK = "nack"
