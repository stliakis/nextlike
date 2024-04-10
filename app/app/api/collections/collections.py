from sqlalchemy.orm import Session

from app.api.deps import get_database, get_organization
from app.api.events.types import (
    CollectionEventsResetRequest,
    CollectionEventsResetResponse,
)

from fastapi import APIRouter, Depends

from app.models.organization import Organization
from app.resources.database import m

router = APIRouter()


@router.delete("/api/collections", response_model=CollectionEventsResetResponse)
def collection_delete(
        delete_request: CollectionEventsResetRequest,
        db: Session = Depends(get_database),
        organization: Organization = Depends(get_organization),
) -> CollectionEventsResetResponse:
    collection = m.Collection.objects(db).get_or_create(delete_request.collection, organization)

    collection = (
        m.Collection.objects(db)
        .filter(m.Collection.name == delete_request.collection)
        .first()
    )
    collection.delete()
    return CollectionEventsResetResponse(
        message=f"Collection {delete_request.collection} has been deleted"
    )
