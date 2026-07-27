from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PubSubConfig:
    project_id: str
    credentials_path: Optional[str] = None  # sets GOOGLE_APPLICATION_CREDENTIALS if provided


@dataclass
class PublishOptions:
    attributes: Optional[dict[str, str]] = None
    ordering_key: Optional[str] = None


@dataclass
class SubscriptionOptions:
    ack_deadline_seconds: int = 10
    enable_message_ordering: bool = False
    dead_letter_topic: Optional[str] = None
    max_delivery_attempts: Optional[int] = None


@dataclass
class PulledMessage:
    ack_id: str
    message_id: str
    data: bytes
    attributes: dict[str, str] = field(default_factory=dict)
    ordering_key: Optional[str] = None

