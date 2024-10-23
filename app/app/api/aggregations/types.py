from typing import List, Optional

from pydantic.main import BaseModel

from app.recommender.types import AggregationConfig, HeavyAndLightLLMStats


class AggregationRequest(BaseModel):
    collection: str
    config: AggregationConfig


class AggregationResponse(BaseModel):
    aggregation: str
    items: List[dict]
    llm_stats: HeavyAndLightLLMStats = None


class AggregationResponseError(BaseModel):
    error: Optional[str]
