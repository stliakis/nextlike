from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import sqlalchemy
from sqlalchemy import Column, String, BigInteger, func, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import BaseAlchemyModel, BaseModelManager
from app.models.logging import StoredLogs
from app.resources.database import m
from app.schemas.collection import CollectionSchema
from app.utils.base import default_ns_id, repr_string


class Collection(BaseAlchemyModel):
    PydanticModel = CollectionSchema

    id = Column(BigInteger, primary_key=True, default=default_ns_id)
    organization_id = Column(BigInteger, ForeignKey(m.Organization.id, ondelete="CASCADE"))
    organization = relationship(m.Organization)
    default_embeddings_model = Column(String, nullable=True)
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
        m.Item.objects(db).filter(m.Item.collection == self)
        m.ItemsField.objects(db).filter(m.ItemsField.collection == self)
        m.Person.objects(db).filter(m.Person.collection == self)
        m.PersonsField.objects(db).filter(m.PersonsField.collection == self)
        m.Event.objects(db).filter(m.Event.collection == self)
        self.get_logger().delete_all_logs()
        super(Collection, self).delete(db)

    def __repr__(self):
        return repr_string(self, ["id", "name", "organization_id"])
