from typing import List, Union

from pydantic.main import BaseModel

from app.core.types import SimpleItem


class ItemsIngestRequest(BaseModel):
    items: List[SimpleItem]
    collection: str
    recalculate_vectors: bool = False
    model: str = None
    sync: bool = False


class ItemsDeletionRequest(BaseModel):
    ids: List[str]
    collection: str
    sync: bool = False

class CollectionItemsResetRequest(BaseModel):
    collection: str


class ItemsIngestResponse(BaseModel):
    message: str


class ItemsDeletionResponse(BaseModel):
    message: str


class CollectionItemsResetResponse(BaseModel):
    message: str
