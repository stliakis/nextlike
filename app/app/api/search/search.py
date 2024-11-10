import time

from sqlalchemy.orm import Session
from typing import Union

from app.api.deps import get_database, get_organization
from app.exceptions import ItemNotFound
from app.logger import logger
from app.models.organization import Organization
from app.core.searcher.searcher import Searcher
from app.api.search.types import (
    SearchRequest,
    SearchResponse,
    SearchResponseError,
)
from fastapi import APIRouter, HTTPException, Depends

from app.resources.database import m

router = APIRouter()


@router.post("/api/search", response_model=SearchResponse)
async def search(
        search_request: SearchRequest,
        db: Session = Depends(get_database),
        organization: Organization = Depends(get_organization),
) -> Union[SearchResponse, SearchResponseError]:
    begin = time.time()

    logger.info(f"Received search request: {search_request}")

    collection = m.Collection.objects(db).get_or_create(
        search_request.collection, organization
    )

    search_engine = Searcher(
        db=db,
        collection=collection,
        config=search_request.config,
    )

    try:
        search_result =await search_engine.search()
    except ItemNotFound as e:
        raise HTTPException(
            status_code=422,
            detail=f"Item with id {e.item_id} not found in collection {e.collection}",
        )

    took_ms = int((time.time() - begin) * 1000)

    return SearchResponse(items=search_result.items, id=search_result.id, took_ms=took_ms)
