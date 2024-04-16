from sqlalchemy.orm import Session
from typing import List, Tuple

from app.models import Collection
from app.recommender.collaborative_engine import CollaborativeEngine
from app.recommender.embeddings import OpenAiEmbeddingsCalculator
from app.recommender.helpers import get_external_item_ids_of_events_for_user
from app.recommender.similarity_engine import SimilarityEngine
from app.recommender.types import RecommendationConfig, Recommendation
from app.resources.database import m
from app.utils.base import uuid_or_int, listify


class Recommender(object):
    def __init__(self, db: Session, collection: Collection, config: RecommendationConfig):
        self.collection = collection
        self.config = config
        self.db = db
        self.collaborative_engine = CollaborativeEngine(db, collection)
        self.similarity_engine = SimilarityEngine(
            db, collection, OpenAiEmbeddingsCalculator()
        )

    def get_exclude_items(self) -> List[str | int]:
        items_to_exclude = self.config.exclude or []

        if self.config.exclude_already_interacted_with_person:
            items_user_interacted_with = get_external_item_ids_of_events_for_user(
                self.db,
                listify(self.config.exclude_already_interacted_with_person)
            )
            items_to_exclude += [item for item, weight in items_user_interacted_with]

        if self.config.feedlike:
            if self.config.for_person:
                already_served_to_user = m.SearchHistory.objects(self.db).get_external_item_ids_served_to_user(
                    self.config.for_person
                )
                items_to_exclude += already_served_to_user
            else:
                raise Exception("No for_person provided for feedlike recommendation")

        return items_to_exclude

    def log_recommendation_history(self, external_person_id, recommendation):
        item_ids = [item.external_id for item in recommendation.items]
        return m.SearchHistory(
            external_person_id=external_person_id,
            external_item_ids=item_ids,
            search_config=self.config.dict(),
            collection=self.collection
        ).flush(self.db)

    def recommend(self) -> Recommendation:
        excluded = self.get_exclude_items()

        if self.config.similar:
            recommendation = self.similarity_engine.recommend(self.config, exclude=excluded)
        elif self.config.collaborative:
            recommendation = self.collaborative_engine.recommend(self.config, exclude=excluded)
        else:
            raise Exception("No recommendation config provided")

        recommendation_entry = self.log_recommendation_history(self.config.for_person, recommendation)

        recommendation.id = recommendation_entry.id

        return recommendation
