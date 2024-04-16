from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Union, Tuple
from app.models import Item, Collection
from app.recommender.clauses.similarity import PersonToVectorClause, FieldsToVectorClause, ItemToVectorClause, \
    PromptToVectorClause
from app.recommender.embeddings import OpenAiEmbeddingsCalculator
from app.recommender.types import RecommendedItem, RecommendationConfig, Recommendation
from app.resources.database import m
from app.utils.base import get_fields_hash
from app.utils.json_filter_query import build_query_string_and_params


class SimilarityEngine(object):
    def __init__(self, db: Session, collection: Collection, embeddings_calculator=None):
        self.collection = collection
        self.db = db
        self.embeddings_calculator = embeddings_calculator or OpenAiEmbeddingsCalculator()
        self.clauses = [
            PersonToVectorClause,
            ItemToVectorClause,
            FieldsToVectorClause,
            PromptToVectorClause
        ]

    def filter_out_ingested_items(
            self, items: List[Item]
    ) -> List[Item]:
        hashes_in_db = [item.description_hash for item in items]

        changed_items = []
        for item in items:
            if item.get_hash() not in hashes_in_db:
                changed_items.append(item)

        return changed_items

    def get_average_vector_of_vectors(self, vectors):
        return [
            sum([vector[i] for vector in vectors]) / len(vectors)
            for i in range(len(vectors[0]))
        ]

    def get_weighted_vectors(self, query_vectors: List[Tuple[List[int], float]]):
        weighted_vectors = []
        for vector, weight in query_vectors:
            weighted_vectors.append([i * weight for i in vector])

        return weighted_vectors

    def recommend(self, config: RecommendationConfig, exclude: List[str]):
        if not config.similar:
            return Recommendation(items=[])

        vectors: List[Tuple[List[int], float]] = []
        for of in config.similar.of:
            for Clause in self.clauses:
                clause = Clause.from_of(self, of)
                if clause:
                    vectors.extend(clause.get_vectors())

        if len(vectors) == 0:
            return Recommendation(items=[])

        return Recommendation(items=self.get_similar(
            query_vectors=vectors,
            exclude_external_item_ids=exclude,
            limit=config.limit,
            offset=config.offset,
            filters=config.filter,
            score_threshold=config.similar.score_threshold,
            randomize=config.randomize
        ))

    def get_similar(
            self,
            query_vectors: List[Tuple[List[int], float]] = None,
            exclude_external_item_ids: List[Union[int, str]] = None,
            limit: int = 10,
            offset: int = 0,
            filters: Union[dict, None] = None,
            score_threshold=0.01,
            randomize=False
    ):
        query_vectors = self.get_weighted_vectors(query_vectors)

        query_vector = self.get_average_vector_of_vectors(query_vectors)

        all_where_clauses = []
        all_where_params = {}

        if filters:
            filters_query, filter_params = build_query_string_and_params("fields", filters)
            all_where_clauses.append(filters_query)
            all_where_params.update(filter_params)

        if exclude_external_item_ids:
            all_where_clauses.append("not item.external_id = any(:exclude_ids)")
            all_where_params.update({
                "exclude_ids": exclude_external_item_ids
            })

        query_params = {
            "vector": "[%s]" % (",".join(map(str, query_vector))),
            "limit": limit,
            "offset": offset,
            "score_threshold": score_threshold
        }

        query_params.update(all_where_params)

        if randomize:
            order_by = "random()"
        else:
            order_by = "similarity_table.similarity desc"

        query = text("""
           select id,external_id,fields,similarity from (
               select item.id,item.external_id,item.fields,  (item.vectors_1536 <#> :vector)*-1 as similarity from item {where_clauses}
               ) as similarity_table where similarity_table.similarity > :score_threshold order by {order_by} limit :limit offset :offset
           """.format(
            where_clauses=f"where {' and '.join(all_where_clauses)}" if all_where_clauses else "",
            order_by=order_by
        )).params(query_params)

        similar_items = self.db.execute(query).fetchall()

        recommendations = []
        for item in similar_items:
            recommendations.append(RecommendedItem(
                id=item.id,
                external_id=item.external_id,
                fields=item.fields,
                score=item.similarity
            ))

        return recommendations

    def get_query_vector_from_fields(self, fields) -> List[int]:
        description_hash = get_fields_hash(fields)
        matching_item = m.Item.objects(self.db).filter(m.Item.description_hash == description_hash).first()
        if matching_item:
            return matching_item.vectors_1536

        return self.embeddings_calculator.get_embeddings_from_fields(fields)

    def get_query_vector_from_prompt(self, prompt: str) -> List[int]:
        return self.embeddings_calculator.get_embeddings_from_string(prompt)

    def get_embeddings_of_items(self, items, skip_ingested=True):
        if skip_ingested:
            changed_items = self.filter_out_ingested_items(items)
        else:
            changed_items = items

        changed_item_embeddings = self.embeddings_calculator.get_embeddings_from_items(changed_items)

        unchanged_items = [item for item in items if item not in changed_items]

        all_embeddings = {}

        for item, vector in zip(changed_items, changed_item_embeddings):
            item.vector = vector
            all_embeddings[item.id] = vector

        for item in unchanged_items:
            all_embeddings[item.id] = item.vectors_1536

        return all_embeddings
