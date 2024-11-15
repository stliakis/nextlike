from typing import List, Union

from pydantic.main import BaseModel

from app.core.types import SimpleItem, SimpleEvent


class EventsIngestRequest(BaseModel):
    events: List[SimpleEvent]
    collection: str


class CollectionDeleteRequest(BaseModel):
    collection: str


class EventsIngestResponse(BaseModel):
    message: str


class CollectionEventsResetResponse(BaseModel):
    message: str
