from typing import List, Optional

from pydantic.main import BaseModel

from app.core.autocompletor.types import AutoCompleteConfig
from app.core.searcher.types import SearchItem


class AutocompleteRequest(BaseModel):
    collection: str
    config: AutoCompleteConfig


class AutocompleteResponse(BaseModel):
    suggestions: List[SearchItem]
    took_ms: int


class AutocompleteResponseError(BaseModel):
    error: Optional[str]
