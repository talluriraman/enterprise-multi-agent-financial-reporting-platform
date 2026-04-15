import logging
from typing import Any

from app.servicebus.interface import ServiceBusPublisher

logger = logging.getLogger(__name__)


class NoOpServiceBus(ServiceBusPublisher):
    """POC: log-only publisher. Swap for Azure Service Bus in production."""

    async def publish(self, topic: str, body: dict[str, Any], correlation_id: str | None) -> None:
        logger.info("servicebus.noop topic=%s correlation_id=%s body_keys=%s", topic, correlation_id, list(body.keys()))
