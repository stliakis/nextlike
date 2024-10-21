from typing import List, Optional

from pydantic.main import BaseModel

from app.recommender.types import AggregationConfig


class AggregationRequest(BaseModel):
    collection: str
    config: AggregationConfig


class AggregationResponse(BaseModel):
    aggregation: str
    items: List[dict]


class AggregationResponseError(BaseModel):
    error: Optional[str]
