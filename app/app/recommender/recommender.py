from sqlalchemy.orm import Session
from typing import List

from app.models import Collection
from app.recommender.collaborative_engine import CollaborativeEngine
from app.recommender.embeddings import OpenAiEmbeddingsCalculator
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

    def get_exclude_ids(self) -> List[str | int]:
        if self.config.collaborative:
            ids_to_exclude = self.config.collaborative.exclude_ids or []
            if self.config.collaborative.exclude_already_interacted_with_person_id:
                items_user_interacted_with = self.collaborative_engine.get_external_item_ids_of_users(
                    listify(self.config.collaborative.exclude_already_interacted_with_person_id)
                )
                ids_to_exclude += items_user_interacted_with
        elif self.config.similarity:
            ids_to_exclude = self.config.similarity.exclude_ids or []
            if self.config.similarity.exclude_already_interacted_with_person_id:
                items_user_interacted_with = self.collaborative_engine.get_external_item_ids_of_users(
                    listify(self.config.similarity.exclude_already_interacted_with_person_id)
                )
                ids_to_exclude += items_user_interacted_with
        else:
            ids_to_exclude = []

        if self.config.feedlike and self.config.for_person_id:
            already_served_to_user = m.RecommendationHistory.objects(self.db).get_external_item_ids_served_to_user(
                self.config.for_person_id
            )
            ids_to_exclude += already_served_to_user

        return list(map(str, ids_to_exclude))

    def log_recommendation_history(self, external_person_id, recommendation):
        item_ids = [item.external_id for item in recommendation.items]
        return m.RecommendationHistory(
            external_person_id=external_person_id,
            external_item_ids=item_ids,
            recommendation_config=self.config.dict(),
            collection=self.collection
        ).flush(self.db)

    def recommend_by_similarity(self):
        external_item_ids = []
        vector = None

        if self.config.similarity.similar_to_fields:
            vector = self.similarity_engine.get_query_vector(
                fields=self.config.similarity.similar_to_fields
            )
        else:
            if self.config.similarity.similar_to_item_id:
                external_item_ids.extend(listify(self.config.similarity.similar_to_item_id))

            if self.config.similarity.person_id:
                external_item_ids.extend(self.collaborative_engine.get_external_item_ids_of_users(
                    listify(self.config.similarity.person_id)
                ))

        if external_item_ids or vector is not None:
            ids_to_exclude = self.get_exclude_ids()

            items = self.similarity_engine.get_similar(
                query_vector=vector,
                external_item_ids=external_item_ids,
                limit=self.config.limit,
                offset=self.config.offset,
                exclude_external_item_ids=ids_to_exclude,
                filters=self.config.filters,
                randomize=self.config.randomize,
                score_threshold=self.config.similarity.similarity_threshold,
            )
        else:
            items = []

        return Recommendation(items=items)

    def recommend_by_collaborative(self):
        item_ids = []

        if self.config.collaborative.item_id:
            item_ids.extend(listify(self.config.collaborative.item_id))

        if self.config.collaborative.person_id:
            items_seen_by_user = self.collaborative_engine.get_external_item_ids_of_users(
                listify(self.config.collaborative.person_id)
            )
            item_ids.extend(items_seen_by_user)

        if item_ids:
            ids_to_exclude = self.get_exclude_ids()

            items = self.collaborative_engine.get_items_seen_by_others(
                external_item_ids=item_ids,
                limit=self.config.limit,
                exclude_external_item_ids=ids_to_exclude,
                filters=self.config.filters,
                common_events_threshold=self.config.collaborative.minimum_interactions,
                randomize=self.config.randomize,
            )
        else:
            items = []

        return Recommendation(items=items)

    def recommend_by_combined(self):
        raise NotImplementedError()

    def recommend(self) -> Recommendation:
        if self.config.similarity:
            recommendation = self.recommend_by_similarity()
        elif self.config.collaborative:
            recommendation = self.recommend_by_collaborative()
        elif self.config.combined:
            recommendation = self.recommend_by_combined()
        else:
            raise Exception("No recommendation config provided")

        recommendation_entry = self.log_recommendation_history(self.config.for_person_id, recommendation)

        recommendation.id = recommendation_entry.id

        return recommendation
