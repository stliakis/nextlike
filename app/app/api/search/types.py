from typing import Union, List, Optional

from pydantic.main import BaseModel

from app.core.types import SearchConfig, SearchItem


class SearchRequest(BaseModel):
    collection: str
    config: SearchConfig


class SearchResponse(BaseModel):
    items: Optional[List[SearchItem]]
    id: int


class SearchResponseError(BaseModel):
    error: Optional[str]
