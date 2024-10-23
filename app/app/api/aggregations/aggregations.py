from sqlalchemy.orm import Session
from typing import Union

from app.api.aggregations.types import AggregationResponse, AggregationRequest, AggregationResponseError
from app.api.deps import get_database, get_organization
from app.exceptions import ItemNotFound
from app.logger import logger
from app.models.organization import Organization
from app.recommender.aggregations_engine import AggregationsEngine
from fastapi import APIRouter, HTTPException, Depends

from app.resources.database import m
from app.settings import get_settings

router = APIRouter()


@router.post("/api/aggregate", response_model=AggregationResponse)
def recommend(
        aggregation_request: AggregationRequest,
        db: Session = Depends(get_database),
        organization: Organization = Depends(get_organization),
) -> Union[AggregationResponse, AggregationResponseError]:
    logger.info(f"Received aggregation request: {aggregation_request}")

    collection = m.Collection.objects(db).get_or_create(aggregation_request.collection, organization,
                                                        default_embeddings_model=get_settings().AGGREGATIONS_DEFAULT_EMBEDDINGS_MODEL)

    aggregator = AggregationsEngine(
        db=db,
        collection=collection,
        config=aggregation_request.config,
    )

    try:
        aggregation = aggregator.aggregate()
    except ItemNotFound as e:
        raise HTTPException(
            status_code=422,
            detail=f"Item with id {e.item_id} not found in collection {e.collection}",
        )

    return AggregationResponse(
        items=aggregation.items,
        aggregation=aggregation.aggregation,
        llm_stats=aggregation.stats,
    )
