from datetime import datetime
from typing import Union
from uuid import UUID
from pydantic import BaseModel


class CollectionSchema(BaseModel):
    id: int
    name: str
    organization_id: int


class CollectionBase(BaseModel):
    name: str


class CollectionCreate(CollectionBase):
    pass


class CollectionUpdate(CollectionBase):
    pass


class CollectionAPIKeySchema(BaseModel):
    collection_id: int
    secret_key: UUID
    created: Union[datetime, None]

    class Config:
        orm_mode = True
