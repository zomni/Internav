import logging

from app.domain.events import DomainEvent, EventBus, EventType


def _on_organization_created(event: DomainEvent) -> None:
    logger = logging.getLogger("audit.events")
    logger.info("Organization created: id=%s name=%s", event.entity_id, (event.payload or {}).get("name"))


def _on_campaign_started(event: DomainEvent) -> None:
    logger = logging.getLogger("audit.events")
    logger.info("Campaign started: id=%s floor_id=%s", event.entity_id, (event.payload or {}).get("floor_id"))


def _on_fingerprint_captured(event: DomainEvent) -> None:
    logger = logging.getLogger("audit.events")
    logger.info("Fingerprint captured: id=%s campaign=%s cell=%s", event.entity_id, (event.payload or {}).get("campaign_id"), (event.payload or {}).get("cell_id"))


def _on_dataset_built(event: DomainEvent) -> None:
    logger = logging.getLogger("audit.events")
    payload = event.payload or {}
    logger.info("Dataset built: id=%s fp_count=%s floor_count=%s", event.entity_id, payload.get("fingerprint_count"), payload.get("floor_count"))


def _on_training_started(event: DomainEvent) -> None:
    logger = logging.getLogger("audit.events")
    logger.info("Training started: model=%s", event.entity_id)


def _on_training_completed(event: DomainEvent) -> None:
    logger = logging.getLogger("audit.events")
    payload = event.payload or {}
    logger.info("Training completed: model=%s accuracy=%s", event.entity_id, payload.get("metrics", {}).get("accuracy") if isinstance(payload.get("metrics"), dict) else "?")


def _on_model_published(event: DomainEvent) -> None:
    logger = logging.getLogger("audit.events")
    payload = event.payload or {}
    logger.info("Model published: id=%s floor=%s algorithm=%s", event.entity_id, payload.get("floor_id"), payload.get("algorithm"))


def _on_model_downloaded(event: DomainEvent) -> None:
    logger = logging.getLogger("audit.events")
    logger.info("Model downloaded: id=%s", event.entity_id)


def _on_inference_executed(event: DomainEvent) -> None:
    logger = logging.getLogger("audit.events")
    payload = event.payload or {}
    logger.info("Inference executed: model=%s predicted=%s confidence=%s", event.entity_id, payload.get("predicted_cell_id"), payload.get("confidence"))


def _on_model_ready(event: DomainEvent) -> None:
    logger = logging.getLogger("audit.events")
    logger.info("Model ready: id=%s", event.entity_id)


def subscribe_audit_listeners() -> None:
    EventBus.subscribe(EventType.ORGANIZATION_CREATED, _on_organization_created)
    EventBus.subscribe(EventType.CAMPAIGN_STARTED, _on_campaign_started)
    EventBus.subscribe(EventType.FINGERPRINT_CAPTURED, _on_fingerprint_captured)
    EventBus.subscribe(EventType.DATASET_BUILT, _on_dataset_built)
    EventBus.subscribe(EventType.TRAINING_STARTED, _on_training_started)
    EventBus.subscribe(EventType.TRAINING_COMPLETED, _on_training_completed)
    EventBus.subscribe(EventType.MODEL_READY, _on_model_ready)
    EventBus.subscribe(EventType.MODEL_PUBLISHED, _on_model_published)
    EventBus.subscribe(EventType.MODEL_DOWNLOADED, _on_model_downloaded)
    EventBus.subscribe(EventType.INFERENCE_EXECUTED, _on_inference_executed)
