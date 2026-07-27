from typing import Union 
import os
from typing import Callable, Optional
from google.api_core.exceptions import AlreadyExists, NotFound
from google.cloud import pubsub_v1

from ...app_shared.enums import AckAction, PubSubEnvVar
from ...gcp_services.contracts.abstract_pub_sub_service import AbstractPubSubService
from ...gcp_services.models_services.queue_storage import PubSubConfig, PublishOptions, PulledMessage, SubscriptionOptions
from ...utils.queue_config import load_pubsub_config_from_env


class GooglePubSubService(AbstractPubSubService):
    def __init__(self, config: PubSubConfig):
        if config.credentials_path:
            os.environ[PubSubEnvVar.CREDENTIALS_PATH.value] = config.credentials_path

        self.project_id = config.project_id
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()

    @classmethod
    def from_env(cls) -> "GooglePubSubService":
        """Convenience factory that reads config from environment variables."""
        return cls(load_pubsub_config_from_env())


    def _topic_path(self, topic_name: str) -> str:
        return self.publisher.topic_path(self.project_id, topic_name)

    def _subscription_path(self, subscription_name: str) -> str:
        return self.subscriber.subscription_path(self.project_id, subscription_name)


    def create_topic(self, topic_name: str) -> str:
        topic_path = self._topic_path(topic_name)
        try:
            self.publisher.create_topic(request={"name": topic_path})
        except AlreadyExists:
            pass
        return topic_path

    def delete_topic(self, topic_name: str) -> None:
        topic_path = self._topic_path(topic_name)
        try:
            self.publisher.delete_topic(request={"topic": topic_path})
        except NotFound:
            pass

    def topic_exists(self, topic_name: str) -> bool:
        try:
            self.publisher.get_topic(request={"topic": self._topic_path(topic_name)})
            return True
        except NotFound:
            return False

    def list_topics(self) -> list[str]:
        project_path = f"projects/{self.project_id}"
        return [
            topic.name.split("/")[-1]
            for topic in self.publisher.list_topics(request={"project": project_path})
        ]


    def create_subscription(
        self,
        topic_name: str,
        subscription_name: str,
        options: Optional[SubscriptionOptions] = None,
    ) -> str:
        options = options or SubscriptionOptions()
        subscription_path = self._subscription_path(subscription_name)

        request = {
            "name": subscription_path,
            "topic": self._topic_path(topic_name),
            "ack_deadline_seconds": options.ack_deadline_seconds,
            "enable_message_ordering": options.enable_message_ordering,
        }

        if options.dead_letter_topic:
            dead_letter_policy = {
                "dead_letter_topic": self._topic_path(options.dead_letter_topic),
            }
            if options.max_delivery_attempts:
                dead_letter_policy["max_delivery_attempts"] = options.max_delivery_attempts
            request["dead_letter_policy"] = dead_letter_policy

        try:
            self.subscriber.create_subscription(request=request)
        except AlreadyExists:
            pass
        return subscription_path

    def delete_subscription(self, subscription_name: str) -> None:
        try:
            self.subscriber.delete_subscription(
                request={"subscription": self._subscription_path(subscription_name)}
            )
        except NotFound:
            pass

    def subscription_exists(self, subscription_name: str) -> bool:
        try:
            self.subscriber.get_subscription(
                request={"subscription": self._subscription_path(subscription_name)}
            )
            return True
        except NotFound:
            return False

    def list_subscriptions(self, topic_name: Optional[str] = None) -> list[str]:
        if topic_name:
            subs = self.publisher.list_topic_subscriptions(
                request={"topic": self._topic_path(topic_name)}
            )
            return [sub.split("/")[-1] for sub in subs]

        project_path = f"projects/{self.project_id}"
        subs = self.subscriber.list_subscriptions(request={"project": project_path})
        return [sub.name.split("/")[-1] for sub in subs]

    # ---- Publish ----

    def publish_message(
        self,
        topic_name: str,
        data: Union[bytes, str],
        options: Optional[PublishOptions] = None,
    ) -> str:
        options = options or PublishOptions()

        if isinstance(data, str):
            data = data.encode("utf-8")

        kwargs = {}
        if options.attributes:
            kwargs.update(options.attributes)
        if options.ordering_key:
            kwargs["ordering_key"] = options.ordering_key

        future = self.publisher.publish(self._topic_path(topic_name), data, **kwargs)
        return future.result()  # blocks until publish confirms, returns message_id

    # ---- Pull (synchronous) ----

    def pull_messages(
        self, subscription_name: str, max_messages: int = 10
    ) -> list[PulledMessage]:
        subscription_path = self._subscription_path(subscription_name)

        response = self.subscriber.pull(
            request={
                "subscription": subscription_path,
                "max_messages": max_messages,
            }
        )

        return [
            PulledMessage(
                ack_id=msg.ack_id,
                message_id=msg.message.message_id,
                data=msg.message.data,
                attributes=dict(msg.message.attributes),
                ordering_key=msg.message.ordering_key or None,
            )
            for msg in response.received_messages
        ]

    def acknowledge_messages(self, subscription_name: str, ack_ids: list[str]) -> None:
        if not ack_ids:
            return
        self.subscriber.acknowledge(
            request={
                "subscription": self._subscription_path(subscription_name),
                "ack_ids": ack_ids,
            }
        )

    def nack_messages(self, subscription_name: str, ack_ids: list[str]) -> None:
        if not ack_ids:
            return
        # Setting the ack deadline to 0 immediately makes the message
        # available for redelivery, i.e. a "nack".
        self.subscriber.modify_ack_deadline(
            request={
                "subscription": self._subscription_path(subscription_name),
                "ack_ids": ack_ids,
                "ack_deadline_seconds": 0,
            }
        )

    # ---- Subscribe (streaming) ----

    def subscribe_streaming(
        self,
        subscription_name: str,
        callback: Callable[[PulledMessage], AckAction],
    ):
        subscription_path = self._subscription_path(subscription_name)

        def _wrapped_callback(message: pubsub_v1.subscriber.message.Message) -> None:
            pulled = PulledMessage(
                ack_id=message.ack_id,
                message_id=message.message_id,
                data=message.data,
                attributes=dict(message.attributes),
                ordering_key=message.ordering_key or None,
            )
            action = callback(pulled)
            if action == AckAction.ACK:
                message.ack()
            else:
                message.nack()

        streaming_future = self.subscriber.subscribe(subscription_path, callback=_wrapped_callback)
        return streaming_future


# # ------------------------------------------------------------
# # Usage example
# # ------------------------------------------------------------
# if __name__ == "__main__":
#     pubsub = GooglePubSubService.from_env()

#     # Create topic + subscription
#     pubsub.create_topic("book-events")
#     pubsub.create_subscription("book-events", "book-events-sub")

#     # Publish
#     message_id = pubsub.publish_message(
#         "book-events",
#         "book uploaded",
#         PublishOptions(attributes={"source": "inventory-service"}),
#     )
#     print("Published:", message_id)

#     # Pull once
#     messages = pubsub.pull_messages("book-events-sub", max_messages=5)
#     for m in messages:
#         print(m.message_id, m.data)
#     pubsub.acknowledge_messages("book-events-sub", [m.ack_id for m in messages])

#     # Streaming subscribe example
#     def handle_message(msg: PulledMessage) -> AckAction:
#         print("Received:", msg.data)
#         return AckAction.ACK

#     future = pubsub.subscribe_streaming("book-events-sub", handle_message)
#     try:
#         future.result(timeout=30)  # listen for 30 seconds
#     except Exception:
#         future.cancel()