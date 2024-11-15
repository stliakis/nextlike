from sqlalchemy.orm import Session

from app.api.deps import get_database, get_organization
from app.api.events.types import (
    CollectionDeleteRequest,
    CollectionEventsResetResponse, CollectionConfigRequest, CollectionConfigUpdateResponse,
)

from fastapi import APIRouter, Depends

from app.models.organization import Organization
from app.resources.database import m

router = APIRouter()


@router.delete("/api/collections", response_model=CollectionEventsResetResponse)
def collection_delete(
        delete_request: CollectionDeleteRequest,
        db: Session = Depends(get_database),
        organization: Organization = Depends(get_organization),
) -> CollectionEventsResetResponse:
    collection = (
        m.Collection.objects(db)
        .filter(m.Collection.name == delete_request.collection, m.Collection.organization == organization)
        .first()
    )
    if collection:
        collection.delete()
        return CollectionEventsResetResponse(
            message=f"Collection {delete_request.collection} has been deleted"
        )
    else:
        return CollectionEventsResetResponse(
            message=f"Collection {delete_request.collection} not found"
        )


@router.put("/api/collections", response_model=CollectionConfigUpdateResponse)
def collection_config(
        collection_config_request: CollectionConfigRequest,
        db: Session = Depends(get_database),
        organization: Organization = Depends(get_organization),
) -> CollectionEventsResetResponse:
    collection = m.Collection.objects(db).get_or_create(collection_config_request.collection, organization)

    collection.update_config(collection_config_request.config.dict())

    return CollectionEventsResetResponse(
        message=f"Collection config updated"
    )
