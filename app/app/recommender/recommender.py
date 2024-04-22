from sqlalchemy.orm import Session
from typing import List

from app.models import Collection
from app.recommender.clauses.base import get_item_ids_from_ofs
from app.recommender.collaborative_engine import CollaborativeEngine
from app.recommender.embeddings import OpenAiEmbeddingsCalculator
from app.recommender.similarity_engine import SimilarityEngine
from app.recommender.types import RecommendationConfig, Recommendation
from app.resources.database import m
from app.utils.base import listify


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
        items_to_exclude = []

        if self.config.exclude:
            items_to_exclude.extend(listify(get_item_ids_from_ofs(self.db, self.config.exclude)))

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
        item_ids = [item.id for item in recommendation.items]
        return m.SearchHistory(
            external_person_id=external_person_id,
            external_item_ids=item_ids,
            search_config=self.config.dict(),
            collection=self.collection
        ).flush(self.db)

    def recommend(self) -> Recommendation:
        excluded = self.get_exclude_items()

        recommendations = []

        if self.config.similar:
            recommendations.extend(self.similarity_engine.recommend(self.config, exclude=excluded))

        if len(recommendations) < self.config.limit and self.config.collaborative:
            recommendations.extend(self.collaborative_engine.recommend(self.config, exclude=excluded))

        recommendation = Recommendation(items=recommendations)

        recommendation_entry = self.log_recommendation_history(self.config.for_person, recommendation)

        recommendation.id = recommendation_entry.id

        return recommendation
