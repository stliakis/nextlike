from typing import List, Optional

from pydantic.main import BaseModel

from app.core.types import Suggestion, AutoCompleteConfig, SearchItem


class AutocompleteRequest(BaseModel):
    collection: str
    config: AutoCompleteConfig


class AutocompleteResponse(BaseModel):
    suggestions: List[SearchItem]
    took_ms: int


class AutocompleteResponseError(BaseModel):
    error: Optional[str]
