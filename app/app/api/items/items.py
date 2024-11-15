from sqlalchemy.orm import Session

from app.api.deps import get_database, get_organization
from app.models import Collection
from app.models.organization import Organization
from app.resources.database import m
from app.settings import get_settings
from app.api.items.types import (
    ItemsIngestRequest,
    ItemsDeletionRequest,
    ItemsIngestResponse,
    ItemsDeletionResponse,
)
from app.tasks.items import ingest_items, delete_items
from more_itertools import batched
from fastapi import APIRouter, HTTPException, Depends

from app.utils.base import chunks

router = APIRouter()


@router.post("/api/items", response_model=ItemsIngestResponse)
async def items_ingest(
        ingest_request: ItemsIngestRequest, db: Session = Depends(get_database),
        organization: Organization = Depends(get_organization),
) -> ItemsIngestResponse:
    if len(ingest_request.items) > 1000000:
        raise HTTPException(
            status_code=422,
            detail="too many items to ingest at once. Please use batches of 1000000 items.",
        )

    collection = m.Collection.objects(db).get_or_create(ingest_request.collection, organization)

    if collection.default_embeddings_model is None:
        collection.default_embeddings_model = ingest_request.model or get_settings().DEFAULT_EMBEDDINGS_MODEL
        collection.flush()

    for batch in chunks(ingest_request.items, get_settings().INGEST_BATCH_SIZE):
        if ingest_request.sync:
            ingest_items(collection.id, batch, ingest_request.recalculate_vectors, ingest_request.model)
        else:
            ingest_items.delay(collection.id, batch, ingest_request.recalculate_vectors, ingest_request.model)

    return ItemsIngestResponse(
        message=f"scheduled {len(ingest_request.items)} items for ingestion"
    )


@router.delete("/api/items", response_model=ItemsDeletionResponse)
async def items_delete(
        delete_request: ItemsDeletionRequest, db: Session = Depends(get_database)
) -> ItemsDeletionResponse:
    collection = (
        Collection.objects(db)
        .filter(Collection.name == delete_request.collection)
        .first()
    )

    for batch in chunks(delete_request.ids, get_settings().DELETE_BATCH_SIZE):
        if delete_request.sync:
            delete_items(collection.id, batch)
        else:
            delete_items.delay(collection.id, batch)

    return ItemsDeletionResponse(
        message=f"scheduled {len(delete_request.ids)} items for deletion"
    )
