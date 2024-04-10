from __future__ import annotations

from sqlalchemy import Column, String, BigInteger
from app.db.base_class import BaseAlchemyModel, BaseModelManager
from app.resources.database import m
from app.schemas.collection import CollectionSchema
from app.utils.base import default_ns_id


class Organization(BaseAlchemyModel):
    PydanticModel = CollectionSchema

    id = Column(BigInteger, primary_key=True, default=default_ns_id)
    name = Column(String, nullable=True)

    class Manager(BaseModelManager):
        def get_or_create(self, name):
            organization = self.filter(m.Organization.name == name).first()
            if not organization:
                organization = m.Organization().set(name=name)
                organization.flush(self.db)
            return organization

    @classmethod
    def objects(cls, db=None) -> Manager:
        return cls.create_objects_manager(cls.Manager, db=db)
