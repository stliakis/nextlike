from typing import List, Optional

from pydantic.main import BaseModel

from app.core.types import AggregationConfig, AggregationResult, SuggestConfig, Suggestion


class SuggestionsRequest(BaseModel):
    config: SuggestConfig


class SuggestionsResponse(BaseModel):
    suggestions: List[Suggestion]
    took_ms: int


class SuggestionResponseError(BaseModel):
    error: Optional[str]
