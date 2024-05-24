from __future__ import annotations

import json

import hashlib

from sqlalchemy import Column, String, BigInteger, DateTime, func, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB

from app.recommender.types import SimpleItem
from app.resources.database import m
from app.db.base_class import BaseAlchemyModel, BaseModelManager
from app.schemas.recommendations.item import ItemSchema
from app.utils.base import default_ns_id, repr_string, listify
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import mapped_column, relationship


class Item(BaseAlchemyModel):
    PydanticModel = ItemSchema

    id = Column(BigInteger, primary_key=True, default=default_ns_id)
    external_id = Column(String, nullable=False, index=True)
    fields = Column(JSONB, default={}, nullable=False)
    scores = Column(JSONB, default={}, nullable=True)
    description = Column(String, nullable=True, default=None)
    description_hash = Column(String, nullable=True, default=None, index=True)
    created = Column(DateTime, default=func.now())
    last_update = Column(DateTime, default=func.now())
    collection_id = Column(BigInteger, ForeignKey(m.Collection.id, ondelete="CASCADE"), primary_key=True, index=True)
    collection = relationship(m.Collection)
    vectors_1536 = mapped_column(Vector(1536))
    vectors_3072 = mapped_column(Vector(3072))

    class Manager(BaseModelManager):
        def get_by_external_id(self, external_id, collection_id=None):
            query = self.filter(Item.external_id == external_id)
            if collection_id:
                query = query.filter(Item.collection_id == collection_id)

            return query.first()

        # @cached(
        #     lambda self, collection_id, internal_id: "Item.Manager.get_internal_id_from_external_id(%s,%s)"
        #                                              % (collection_id, internal_id),
        #     expire=3600 * 24,
        # )
        def get_internal_id_from_external_id(self, collection_id, external_id):
            obj = self.filter(
                self.Model.collection_id == collection_id,
                self.Model.external_id == external_id,
            ).first()
            if obj:
                return obj.id
            return None

        # @cached(
        #     lambda self, internal_id: "Item.Manager.get_external_id_from_internal_id(%s)"
        #                               % internal_id,
        #     expire=3600 * 24,
        # )
        def get_external_id_from_internal_id(self, internal_id):
            obj = self.get(internal_id)
            if obj:
                return obj.external_id
            return None

        # @cached(
        #     lambda self, collection_id, internal_id: "Item.Manager.get_normalized_internal_id_from_external_id(%s,%s)"
        #                                              % (collection_id, internal_id),
        #     expire=3600 * 24,
        # )
        def get_normalized_internal_id_from_external_id(
                self, collection_id, external_id
        ):
            ##TODO: group the same items from differents orgs and return a unique id
            return self.get_internal_id_from_external_id(collection_id, external_id)

    @property
    def vector(self):
        if self.vectors_3072 is not None:
            return self.vectors_3072
        elif self.vectors_1536 is not None:
            return self.vectors_1536

    @vector.setter
    def vector(self, value):
        if value is not None and len(value) == 3072:
            self.vectors_3072 = value
        elif value is not None and len(value) == 1536:
            self.vectors_1536 = value
        else:
            self.vectors_1536 = None
            self.vectors_3072 = None

    @classmethod
    def objects(cls, db=None) -> Manager:
        return cls.create_objects_manager(cls.Manager, db=db)

    def update_from_simple_item(self, item: SimpleItem):
        if self.fields:
            self.fields.update(item.fields)
        else:
            self.fields = item.fields

        if item.description:
            self.description = item.description
        elif item.description_from_fields:
            self.description = self.fields_to_string(
                {k: v for k, v in item.fields.items() if k in item.description_from_fields})
        else:
            self.description = self.fields_to_string(item.fields)

    def fields_to_string(self, fields):
        return "\n".join(
            [
                f"{key} is {' '.join(map(str, listify(value)))}"
                for key, value in fields.items()
            ]
        )

    def get_fields_with_hash(self):
        return {
            **self.fields,
            "_hash": self.get_hash()
        }

    def get_hash(self):
        return hashlib.md5(f"${json.dumps(self.description)}".encode("utf-8")).hexdigest()

    def __repr__(self):
        return repr_string(self, ["id", "external_id", "fields", "collection_id"])

    def to_dict(self, fields=None):
        return {
            "external_id": self.external_id,
            "id": self.id,
            "created": self.created,
            "fields": [
                {"field": field, "value": self.fields.get(field)}
                for field in (fields or self.fields)
            ],
        }
