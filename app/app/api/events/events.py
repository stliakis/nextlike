from sqlalchemy.orm import Session

from app.api.deps import get_database, get_organization
from app.models import Collection
from app.models.organization import Organization
from app.resources.database import m
from app.settings import get_settings
from app.api.events.types import (
    EventsIngestRequest,
    CollectionEventsResetRequest,
    EventsIngestResponse,
    CollectionEventsResetResponse,
)
from app.tasks.events import ingest_events, cleanup_events
from more_itertools import batched
from fastapi import APIRouter, HTTPException, Depends

router = APIRouter()


@router.post("/api/events", response_model=EventsIngestResponse)
def events_ingest(
        ingest_request: EventsIngestRequest, db: Session = Depends(get_database),
        organization: Organization = Depends(get_organization),
) -> EventsIngestResponse:
    collection = m.Collection.objects(db).get_or_create(ingest_request.collection, organization)

    if len(ingest_request.events) > 1000000:
        raise HTTPException(
            status_code=422,
            detail="Too many events to ingest at once. Please use batches of 1000000 events.",
        )

    for batch in batched(ingest_request.events, get_settings().INGEST_BATCH_SIZE):
        ingest_events.delay(collection.id, batch)

    return EventsIngestResponse(
        message=f"Scheduled {len(ingest_request.events)} events for ingestion"
    )


@router.delete("/api/events", response_model=CollectionEventsResetResponse)
def events_delete(
        delete_request: CollectionEventsResetRequest, db: Session = Depends(get_database)
) -> CollectionEventsResetResponse:
    collection = (
        Collection.objects(db)
        .filter(Collection.name == delete_request.collection)
        .first()
    )
    cleanup_events.delay(collection.id)
    return CollectionEventsResetResponse(
        message=f"Collection {delete_request.collection} events have been flushed"
    )
