from __future__ import annotations

from datetime import datetime, timedelta

import sqlalchemy
from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.db.base_class import BaseAlchemyModel, BaseModelManager
from app.resources.database import m
from app.schemas.recommendations.event import EventSchema
from app.utils.base import default_ns_id


class Event(BaseAlchemyModel):
    PydanticModel = EventSchema

    id = Column(BigInteger, primary_key=True, default=default_ns_id)
    event_type = Column(String, nullable=False)
    person_external_id = Column(String)
    item_external_id = Column(String)
    weight = Column(Float, default=1)
    created: datetime = Column(DateTime, server_default=sqlalchemy.sql.func.now())
    collection_id = Column(BigInteger, ForeignKey(m.Collection.id, ondelete="CASCADE"), primary_key=True)
    related_recommendation_id = Column(BigInteger, ForeignKey(m.RecommendationHistory.id, ondelete="CASCADE"),
                                       nullable=True)
    collection = relationship(m.Collection, back_populates="events")

    class Manager(BaseModelManager):
        def get_active_person_ids_of_last_seconds(self, collection_id: int, seconds: int):
            rows = Event.objects(self.db).distinct(Event.person_external_id).filter(
                Event.collection_id == collection_id,
                Event.created > datetime.now() - timedelta(seconds=seconds))

            return [i.person_external_id for i in rows]

    @classmethod
    def objects(cls, db=None) -> Manager:
        return cls.create_objects_manager(cls.Manager, db=db)

    def to_dict(self):
        return {
            "event_type": self.event_type,
            "item_external_id": self.item_external_id,
            "person_external_id": self.person_external_id,
            "date": self.created
        }
