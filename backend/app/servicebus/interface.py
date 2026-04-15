from typing import Any, Protocol


class ServiceBusPublisher(Protocol):
    """Abstraction for async job fan-out. Production: Azure Service Bus topics."""

    async def publish(self, topic: str, body: dict[str, Any], correlation_id: str | None) -> None: ...


class ServiceBusSubscriber(Protocol):
    async def subscribe(self, topic: str, handler) -> None: ...
