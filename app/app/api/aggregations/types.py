from typing import List, Optional

from pydantic.main import BaseModel

from app.core.types import AggregationConfig, AggregationResult


class AggregationRequest(BaseModel):
    collection: str
    config: AggregationConfig


class AggregationResponse(BaseModel):
    aggregations: List[AggregationResult]


class AggregationResponseError(BaseModel):
    error: Optional[str]
