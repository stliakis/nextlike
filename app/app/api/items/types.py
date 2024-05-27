from typing import List, Union

from pydantic.main import BaseModel

from app.recommender.types import SimpleItem


class ItemsIngestRequest(BaseModel):
    items: List[SimpleItem]
    collection: str
    recalculate_vectors: bool = False
    model: str = None


class ItemsDeletionRequest(BaseModel):
    ids: List[Union[int, str]]
    collection: str


class CollectionItemsResetRequest(BaseModel):
    collection: str


class ItemsIngestResponse(BaseModel):
    message: str


class ItemsDeletionResponse(BaseModel):
    message: str


class CollectionItemsResetResponse(BaseModel):
    message: str
