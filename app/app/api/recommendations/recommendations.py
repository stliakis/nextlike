from sqlalchemy.orm import Session
from typing import Union

from app.api.deps import get_database, get_organization
from app.exceptions import ItemNotFound
from app.logger import logger
from app.models.organization import Organization
from app.recommender.recommender import Recommender
from app.api.recommendations.types import (
    RecommendRequest,
    RecommendResponse,
    RecommendResponseError,
)
from fastapi import APIRouter, HTTPException, Depends

from app.resources.database import m

router = APIRouter()


@router.post("/api/search", response_model=RecommendResponse)
def recommend(
        similar_request: RecommendRequest,
        db: Session = Depends(get_database),
        organization: Organization = Depends(get_organization),
) -> Union[RecommendResponse, RecommendResponseError]:
    logger.info(f"Received recommend request: {similar_request}")

    collection = m.Collection.objects(db).get_or_create(similar_request.collection, organization)

    recommender = Recommender(
        db=db,
        collection=collection,
        config=similar_request.config,
    )

    try:
        recommendation = recommender.recommend()
    except ItemNotFound as e:
        raise HTTPException(
            status_code=422,
            detail=f"Item with id {e.item_id} not found in collection {e.collection}",
        )

    return RecommendResponse(
        items=recommendation.items,
        id=recommendation.id
    )
