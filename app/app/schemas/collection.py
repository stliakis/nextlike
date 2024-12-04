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


class CollectionConfig(BaseModel):
    indexer: str = None
    embeddings_model: str = None
    stemmer = ["english"]
