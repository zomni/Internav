from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, ClassVar
from uuid import UUID


class EventType(StrEnum):
    ORGANIZATION_CREATED = "OrganizationCreated"
    CAMPAIGN_STARTED = "CampaignStarted"
    FINGERPRINT_CAPTURED = "FingerprintCaptured"
    DATASET_BUILT = "DatasetBuilt"
    TRAINING_STARTED = "TrainingStarted"
    TRAINING_COMPLETED = "TrainingCompleted"
    MODEL_READY = "ModelReady"
    MODEL_PUBLISHED = "ModelPublished"
    MODEL_DOWNLOADED = "ModelDownloaded"
    INFERENCE_EXECUTED = "InferenceExecuted"


@dataclass
class DomainEvent:
    event_type: EventType
    entity_id: UUID
    payload: dict[str, Any] | None = None


EventListener = Callable[[DomainEvent], None]


class EventBus:
    _listeners: ClassVar[dict[EventType, list[EventListener]]] = {}

    @classmethod
    def subscribe(cls, event_type: EventType, listener: EventListener) -> None:
        cls._listeners.setdefault(event_type, []).append(listener)

    @classmethod
    def publish(cls, event: DomainEvent) -> None:
        for listener in cls._listeners.get(event.event_type, []):
            listener(event)

    @classmethod
    def reset(cls) -> None:
        cls._listeners.clear()
