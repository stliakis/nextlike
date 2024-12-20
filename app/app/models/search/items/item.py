from __future__ import annotations

import json

import hashlib
from logging import INFO

from sqlalchemy import Column, String, BigInteger, DateTime, func, ForeignKey, text, Index, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import deferred

from app.core.types import SimpleItem, CacheConfig
from app.llm.llm import get_llm
from app.resources.database import m
from app.db.base_class import BaseAlchemyModel, BaseModelManager
from app.schemas.search.item import ItemSchema
from app.settings import get_settings
from app.utils.base import default_ns_id, repr_string, listify
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import mapped_column, relationship

from app.utils.logging import log


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
    vectors_768 = deferred(mapped_column(Vector(768)))
    vectors_1536 =  deferred(mapped_column(Vector(1536)))
    vectors_3072 =  deferred(mapped_column(Vector(3072)))
    vectors_384 =  deferred(mapped_column(Vector(384)))

    is_embeddings_dirty = Column(Boolean, default=False, index=True)
    is_index_dirty = Column(Boolean, default=False, index=True)

    __table_args__ = (
        Index('item_description_idx', "description",
              postgresql_ops={"description": "gin_trgm_ops"},
              postgresql_using='gin'),
        Index("item_vectors_1536", "vectors_1536",
              postgresql_ops={"vectors_1536": "vector_cosine_ops"},
              postgresql_using='hnsw'),
        Index("item_vectors_768", "vectors_768",
              postgresql_ops={"vectors_768": "vector_cosine_ops"},
              postgresql_using='hnsw'),
    )

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
        elif self.vectors_768 is not None:
            return self.vectors_768
        elif self.vectors_384 is not None:
            return self.vectors_384

    @vector.setter
    def vector(self, value):
        self.vectors_1536 = None
        self.vectors_3072 = None
        self.vectors_768 = None
        self.vectors_384 = None

        if value is not None and len(value) == 3072:
            self.vectors_3072 = value
        elif value is not None and len(value) == 1536:
            self.vectors_1536 = value
        elif value is not None and len(value) == 768:
            self.vectors_768 = value
        elif value is not None and len(value) == 384:
            self.vectors_384 = value

    async def update_vector(self, vector):
        self.vector = vector
        self.description_hash = self.get_hash()

    @classmethod
    def objects(cls, db=None) -> Manager:
        return cls.create_objects_manager(cls.Manager, db=db)

    def update_from_simple_item(self, item: SimpleItem):
        if self.fields:
            self.fields.update(item.fields)
        else:
            self.fields = item.fields

        if item.description:
            description = item.description
        elif item.description_from_fields:
            description = self.fields_to_string(
                {k: v for k, v in item.fields.items() if k in item.description_from_fields})
        else:
            description = self.fields_to_string(item.fields)

        if item.description_preprocess:
            description = self.preprocess_description(description, item.description_preprocess)

        self.description = description

        self.scores = item.scores or {}

    def preprocess_description(self, description, preprocess):
        llm = get_llm(preprocess.model or get_settings().DEFAULT_LLM_PROVIDER_AND_MODEL, cache=CacheConfig(
            expire=3600
        ))

        processed_prompt = llm.single_query(f"{preprocess.prompt}. The text is the following: '{description}'")

        log(INFO, f"processed prompt: {processed_prompt}")

        return processed_prompt

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
