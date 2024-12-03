from __future__ import annotations
from datetime import datetime, timedelta
from operator import index

from sqlalchemy import Column, String, BigInteger, func, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.indexers.redis_indexer import RedisIndexer
from app.core.indexers.sql_indexer import SQLIndexer
from app.db.base_class import BaseAlchemyModel, BaseModelManager
from app.models.logging import StoredLogs
from app.resources.database import m
from app.schemas.collection import CollectionSchema, CollectionConfig
from app.utils.base import default_ns_id, repr_string, deep_merge
from app.utils.logging import log


class Collection(BaseAlchemyModel):
    PydanticModel = CollectionSchema

    id = Column(BigInteger, primary_key=True, default=default_ns_id)
    organization_id = Column(BigInteger, ForeignKey(m.Organization.id, ondelete="CASCADE"))
    organization = relationship(m.Organization)

    _config = Column(JSON)
    name = Column(String, nullable=True)
    items = relationship("Item", cascade="all, delete, delete-orphan", single_parent=True)
    persons = relationship("Person", cascade="all, delete, delete-orphan", single_parent=True)
    events = relationship("Event", cascade="all, delete, delete-orphan", single_parent=True)
    items_fields = relationship("ItemsField", cascade="all, delete, delete-orphan", single_parent=True)
    persons_fields = relationship("PersonsField", cascade="all, delete, delete-orphan", single_parent=True)

    # items_fields = relationship("ItemsField",
    #                             cascade="all, delete, delete-orphan", single_parent=True)
    #
    # person_fields = relationship("PersonsField",
    #                              cascade="all, delete, delete-orphan", single_parent=True)

    def initialize_collection(self):
        return self

    class Manager(BaseModelManager):
        def get_by_name(self, name):
            return self.filter(Collection.name == name).first()

        def get_or_create(self, name, organization):
            collection = self.filter(m.Collection.name == name, m.Collection.organization == organization).first()
            if not collection:
                collection = Collection().set(name=name, organization=organization)
                collection.flush(self.db)

            return collection

        async def refresh_items(self, collection, items):
            if collection.config.embeddings_model:
                items_that_need_to_recalculate_embeddings = [
                    item for item in items if item.embeddings_dirty
                ]

                await collection.calculate_embeddings_for_items(items_that_need_to_recalculate_embeddings)

            items_that_need_to_be_indexed = [
                item for item in items if item.indexed_dirty or item.embeddings_dirty
            ]

            await collection.get_indexer().index_items(items_that_need_to_be_indexed)

            for item in items:
                item.indexed_dirty = False
                item.embeddings_dirty = False

                if not item.description_hash:
                    item.description_hash = item.get_hash()

                self.db.add(item)

            self.db.commit()
            self.db.flush()

    def update_config(self, config):
        self._config = deep_merge(self._config or {}, config)
        self.flag_modified("_config")
        self.flush()

    @property
    def default_config(self):
        return {
            "indexer": "postgres",
            "embeddings_model": None
        }

    @property
    def config(self):
        return CollectionConfig(**deep_merge(self.default_config, self._config or {}))

    def get_embeddings_calculator(self):
        if not self.config.embeddings_model:
            return None

        from app.llm.embeddings import get_embeddings_calculator
        return get_embeddings_calculator(self.config.embeddings_model)

    @classmethod
    def objects(cls, db=None) -> Manager:
        return cls.create_objects_manager(cls.Manager, db=db)

    def to_dict(self):
        return {
            "name": self.name,
            "id": self.id
        }

    def get_popularity_state_event(self):
        return {
            "collection_id": self.id
        }

    def get_items(self):
        return m.Item.objects(self.db).filter(m.Item.collection_id == self.id)

    def get_persons(self):
        return m.Person.objects(self.db).filter(m.Person.collection_id == self.id)

    def get_active_persons(self, days=30):
        return self.get_persons().filter(
            m.Person.last_update > (datetime.now() - timedelta(days=days))
        )

    def get_events(self):
        return m.Event.objects(self.db).filter(m.Event.collection_id == self.id)

    def get_stats_events_histogram(self, from_date=None, to_date=None, grouping="day"):
        buckets = []
        query = self.db.query(
            func.date_trunc(grouping, m.Event.created).label("period"),
            func.count(m.Event.id).label("count"),
        ).group_by(func.date_trunc(grouping, m.Event.created))

        if from_date:
            query = query.filter(m.Event.created > from_date)

        if to_date:
            query = query.filter(m.Event.created < to_date)

        for i in query.all():
            buckets.append({"date": i.period, "count": i.count})
        return buckets

    def get_logger(self) -> StoredLogs:
        return StoredLogs(collection=self)

    def to_log_dict(self):
        return {"collection_id": self.id}

    def delete(self, db=None):
        db = db or self.db
        m.Item.objects(db).filter(m.Item.collection == self).delete()
        m.ItemsField.objects(db).filter(m.ItemsField.collection == self).delete()
        m.Person.objects(db).filter(m.Person.collection == self).delete()
        m.PersonsField.objects(db).filter(m.PersonsField.collection == self).delete()
        m.Event.objects(db).filter(m.Event.collection == self).delete()
        super(Collection, self).delete(db)
        db.commit()
        db.flush()

        # self.get_logger().delete_all_logs()

    def get_indexer(self):
        if self.config.indexer == "redis":
            return RedisIndexer(self.db, self, index_embeddings=True)
        elif self.config.indexer == "postgres":
            return SQLIndexer(self.db, self, index_embeddings=True)
        else:
            log("warning", f"Indexer {self.config.indexer} not found, using default")
            return SQLIndexer(self.db, self, index_embeddings=True)

    def search(self, search_config, context=None):
        from app.core.searcher.searcher import Searcher
        return Searcher(
            db=self.db,
            collection=self,
            config=search_config,
            context=context or {},
        ).search()

    async def calculate_embeddings_for_items(self, items):
        embeddings = self.get_embeddings_calculator().get_embeddings_from_items(items)
        for i, item in enumerate(items):
            await item.update_vector(embeddings[i])
            self.db.add(item)

        self.db.commit()
        self.db.flush()

    def __repr__(self):
        return repr_string(self, ["id", "name", "organization_id"])
