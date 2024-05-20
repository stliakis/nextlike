from sqlalchemy.orm import Session
from typing import List

from app.models import Collection
from app.recommender.clauses.base import get_item_ids_from_ofs
from app.recommender.collaborative_engine import CollaborativeEngine
from app.recommender.embeddings import OpenAiEmbeddingsCalculator
from app.recommender.similarity_engine import SimilarityEngine
from app.recommender.types import RecommendationConfig, Recommendation
from app.resources.cache import get_cache
from app.resources.database import m
from app.utils.base import listify
from app.utils.logging import log


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

        return items_to_exclude

    def log_recommendation_history(self, external_person_id, recommendation):
        item_ids = [item.id for item in recommendation.items]
        return m.SearchHistory(
            external_person_id=external_person_id,
            external_item_ids=item_ids,
            search_config=self.config.dict(),
            collection=self.collection
        ).flush(self.db)

    def get_cache_key(self):
        return str(hash(str(self.config.dict())))

    def get_recommendation(self):
        if self.config.cache and self.config.cache.expire:
            cache_key = self.get_cache_key()
            cached = get_cache().get(cache_key)
            if cached:
                log("info", f"returning recommendations from cache({cache_key})")
                return cached

        excluded = self.get_exclude_items()

        recommendations = []

        if self.config.similar:
            recommendations.extend(self.similarity_engine.recommend(self.config, exclude=excluded))

        if len(recommendations) < self.config.limit and self.config.collaborative:
            recommendations.extend(self.collaborative_engine.recommend(self.config, exclude=excluded))

        recommendation = Recommendation(items=recommendations)

        if self.config.cache and self.config.cache.expire:
            get_cache().set(self.get_cache_key(), recommendation, self.config.cache.expire)

        return recommendation

    def recommend(self) -> Recommendation:

        recommendation = self.get_recommendation()

        recommendation_entry = self.log_recommendation_history(self.config.for_person, recommendation)

        recommendation.id = recommendation_entry.id

        return recommendation
