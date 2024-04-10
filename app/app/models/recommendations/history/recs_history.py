from __future__ import annotations

from sqlalchemy import Column, String, BigInteger, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from app.db.base_class import BaseModelManager, BaseAlchemyModel
from app.resources.database import m
from app.schemas.recommendations.person import PersonSchema
from app.utils.base import default_ns_id


class RecommendationHistory(BaseAlchemyModel):
    PydanticModel = PersonSchema

    id = Column(BigInteger, primary_key=True, default=default_ns_id)
    external_person_id = Column(String, nullable=True, index=True)
    external_item_ids = Column(ARRAY(String), index=True)
    recommendation_config = Column(JSONB, default={}, nullable=False)
    created = Column(DateTime, default=func.now())
    collection_id = Column(BigInteger, ForeignKey(m.Collection.id, ondelete="CASCADE"))
    collection = relationship(m.Collection)

    class Manager(BaseModelManager):
        def get_external_item_ids_served_to_user(self, person_id):
            entries = self.select(m.RecommendationHistory.external_item_ids).filter(
                m.RecommendationHistory.external_person_id == person_id
            ).order_by(m.RecommendationHistory.created.desc()).limit(50).all()

            external_item_ids = []
            for entry in entries:
                external_item_ids += entry.external_item_ids

            return external_item_ids

    @classmethod
    def objects(cls, db=None) -> Manager:
        return cls.create_objects_manager(cls.Manager, db=db)

    def to_dict(self, fields=None):
        return {

        }
