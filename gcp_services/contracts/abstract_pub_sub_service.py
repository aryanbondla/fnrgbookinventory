from abc import ABC, abstractmethod
from typing import Callable, Optional, Union

from fnrgbookinventory.app_shared.enums import AckAction
from fnrgbookinventory.gcp_services.models_services.queue_storage import PublishOptions, PulledMessage, SubscriptionOptions


class AbstractPubSubService(ABC):

    # ---- Topics ----

    @abstractmethod
    def create_topic(self, topic_name: str) -> str:
        """Create a topic. Returns the fully qualified topic path."""
        raise NotImplementedError

    @abstractmethod
    def delete_topic(self, topic_name: str) -> None:
        """Delete a topic."""
        raise NotImplementedError

    @abstractmethod
    def topic_exists(self, topic_name: str) -> bool:
        """Check whether a topic exists."""
        raise NotImplementedError

    @abstractmethod
    def list_topics(self) -> list[str]:
        """List all topic names in the project."""
        raise NotImplementedError

    # ---- Subscriptions ----

    @abstractmethod
    def create_subscription(
        self,
        topic_name: str,
        subscription_name: str,
        options: Optional[SubscriptionOptions] = None,
    ) -> str:
        """Create a subscription on a topic. Returns the subscription path."""
        raise NotImplementedError

    @abstractmethod
    def delete_subscription(self, subscription_name: str) -> None:
        """Delete a subscription."""
        raise NotImplementedError

    @abstractmethod
    def subscription_exists(self, subscription_name: str) -> bool:
        """Check whether a subscription exists."""
        raise NotImplementedError

    @abstractmethod
    def list_subscriptions(self, topic_name: Optional[str] = None) -> list[str]:
        """List subscriptions, optionally filtered to one topic."""
        raise NotImplementedError

    # ---- Publish ----

    @abstractmethod
    def publish_message(
        self,
        topic_name: str,
        data: Union[bytes, str],
        options: Optional[PublishOptions] = None,
    ) -> str:
        """Publish a single message. Returns the published message ID."""
        raise NotImplementedError

    # ---- Pull (synchronous) ----

    @abstractmethod
    def pull_messages(
        self, subscription_name: str, max_messages: int = 10
    ) -> list[PulledMessage]:
        """Pull up to `max_messages` messages once (does not auto-ack)."""
        raise NotImplementedError

    @abstractmethod
    def acknowledge_messages(self, subscription_name: str, ack_ids: list[str]) -> None:
        """Acknowledge a batch of pulled messages by their ack IDs."""
        raise NotImplementedError

    @abstractmethod
    def nack_messages(self, subscription_name: str, ack_ids: list[str]) -> None:
        """Negative-acknowledge messages, making them available for redelivery immediately."""
        raise NotImplementedError

    # ---- Subscribe (streaming) ----

    @abstractmethod
    def subscribe_streaming(
        self,
        subscription_name: str,
        callback: Callable[[PulledMessage], AckAction],
    ):
        """
        Start a long-running streaming pull. `callback` receives each
        message and returns AckAction.ACK or AckAction.NACK.
        Returns a handle/future that can be used to stop listening.
        """
        raise NotImplementedError