from typing import List, Union

from pydantic.main import BaseModel

from app.core.types import SimpleEvent
from app.schemas.collection import CollectionConfig


class EventsIngestRequest(BaseModel):
    events: List[SimpleEvent]
    collection: str


class CollectionDeleteRequest(BaseModel):
    collection: str


class CollectionConfigRequest(BaseModel):
    collection: str
    config: CollectionConfig


class EventsIngestResponse(BaseModel):
    message: str


class CollectionEventsResetResponse(BaseModel):
    message: str


class CollectionConfigUpdateResponse(BaseModel):
    message: str
