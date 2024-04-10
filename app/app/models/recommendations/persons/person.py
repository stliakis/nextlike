from __future__ import annotations

from sqlalchemy import Column, String, JSON, BigInteger, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base_class import BaseModelManager, BaseAlchemyModel
from app.models.collection import Collection
from app.models.recommendations.events.event import Event
from app.models.recommendations.items.item import Item
from app.resources.database import m
from app.schemas.recommendations.person import PersonSchema
from app.utils.base import default_ns_id
from app.utils.cache import cached


class Person(BaseAlchemyModel):
    PydanticModel = PersonSchema

    id = Column(BigInteger, primary_key=True, default=default_ns_id)
    external_id = Column(String, nullable=False, index=True)
    fields = Column(JSON, default={}, nullable=False)
    created = Column(DateTime, default=func.now())
    last_update = Column(DateTime, default=func.now())
    collection_id = Column(BigInteger, ForeignKey(m.Collection.id, ondelete="CASCADE"), primary_key=True)
    collection = relationship(m.Collection)

    class Manager(BaseModelManager):
        def get_by_external_id(self, external_id, collection_id=None):
            query = self.filter(Person.external_id == external_id)
            if collection_id:
                query = query.filter(Person.collection_id == collection_id)

            return query.first()

        @cached(
            lambda self, collection_id, internal_id: "Person.Manager.get_internal_id_from_external_id(%s,%s):1"
                                                     % (collection_id, internal_id),
            expire=3600 * 24,
        )
        def get_internal_id_from_external_id(self, collection_id, external_id):
            obj = self.filter(
                self.Model.collection_id == collection_id,
                self.Model.external_id == external_id,
            ).first()
            if obj:
                return obj.id
            return None

        @cached(
            lambda self, internal_id: "Person.Manager.get_external_id_from_internal_id(%s):1"
                                      % internal_id,
            expire=3600 * 24,
        )
        def get_external_id_from_internal_id(self, internal_id):
            obj = self.get(internal_id)
            if obj:
                return obj.external_id
            return None

    @classmethod
    def objects(cls, db=None) -> Manager:
        return cls.create_objects_manager(cls.Manager, db=db)

    def update_fields(self, fields):
        self.fields.update(fields)
        self.flag_modified("fields")

    def get_items_seen(self):
        external_item_ids = (
            Event.objects(self.db)
            .select(Event.item_external_id)
            .filter(Event.person_external_id == self.external_id)
            .all()
        )
        external_item_ids = [event.item_external_id for event in external_item_ids]

        items = Item.objects(self.db).filter(Item.collection_id == self.collection_id,
                                             Item.external_id.in_(external_item_ids)).limit(1000).all()

        return items

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
