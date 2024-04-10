from typing import List

from pydantic import BaseModel

from app.schemas.collection import CollectionSchema
from app.schemas.user import UserSchema


class OrganizationSchema(BaseModel):
    id: int
    name: str
    collections: List[CollectionSchema]


class UserToOrganizationSchema(BaseModel):
    is_organization_owner: bool
    is_activated: bool
    permissions: List[str]
    user: UserSchema
