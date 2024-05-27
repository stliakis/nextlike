from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Union, Tuple, Dict

from app.llm.llm import LLM
from app.models import Item, Collection
from app.recommender.clauses.base import get_vectors_from_ofs
from app.llm.embeddings import OpenAiEmbeddingsCalculator
from app.recommender.types import RecommendedItem, RecommendationConfig, SortingModifier
from app.resources.database import m
from app.utils.base import get_fields_hash
from app.utils.json_filter_query import build_query_string_and_params


class SimilarityEngine(object):
    def __init__(self, db: Session, collection: Collection, embeddings_calculator=None, llm=None):
        self.collection = collection
        self.db = db
        self.embeddings_calculator = embeddings_calculator or OpenAiEmbeddingsCalculator(
            model=collection.default_embeddings_model)
        self.llm = llm or LLM()

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

    def recommend(self, config: RecommendationConfig, exclude: List[str]) -> List[RecommendedItem]:
        if not config.similar:
            return []

        vectors: List[Tuple[List[int], float]] = []
        vectors.extend(get_vectors_from_ofs(self.db, self, config.similar.of))

        if len(vectors) == 0:
            return []

        return self.get_similar(
            query_vectors=vectors,
            exclude_external_item_ids=exclude,
            limit=config.limit,
            offset=config.offset,
            sort=config.similar.sort,
            filters=config.filter,
            score_threshold=config.similar.score_threshold,
            distance_function=config.similar.distance_function,
            randomize=config.randomize
        )

    def sort_similar_items(self, similar_items, sort, limit, offset):
        max_similarity = max([item.similarity for item in similar_items])
        max_score = max([item.score for item in similar_items])
        min_score = min([item.score for item in similar_items])

        for similar_item in similar_items:
            similar_item.score = (similar_item.score - min_score) / (
                    max_score - min_score) if max_score != min_score else 0
            similar_item.score = similar_item.score * max_similarity * sort.weight + similar_item.similarity * (
                    1 - sort.weight)

        sorted_items = sorted(similar_items, key=lambda x: x.score, reverse=True)
        paginated_items = sorted_items[offset:offset + limit]

        return paginated_items

    def get_similar(
            self,
            query_vectors: List[Tuple[List[int], float]] = None,
            exclude_external_item_ids: List[Union[int, str]] = None,
            limit: int = 10,
            offset: int = 0,
            filters: Union[dict, None] = None,
            sort: SortingModifier = None,
            score_threshold: float = None,
            distance_function="cosine",
            randomize=False
    ):
        query_vectors = self.get_weighted_vectors(query_vectors)

        query_vector = self.get_average_vector_of_vectors(query_vectors)

        all_where_clauses: List[str] = []
        all_where_params: Dict[str, any] = {}

        if filters:
            filters_query, filter_params = build_query_string_and_params("fields", filters)
            all_where_clauses.append(filters_query)
            all_where_params.update(filter_params)

        if exclude_external_item_ids:
            all_where_clauses.append("not item.external_id = any(:exclude_ids)")
            all_where_params.update({
                "exclude_ids": exclude_external_item_ids
            })

        all_where_clauses.append("item.collection_id = :collection_id")
        all_where_params.update({
            "collection_id": self.collection.id
        })

        query_params = {
            "vector": "[%s]" % (",".join(map(str, query_vector))),
            "limit": limit,
            "offset": offset,
            "score_threshold": score_threshold
        }

        if score_threshold:
            score_threshold_query = "similarity_table.similarity > :score_threshold"
            query_params["score_threshold"] = score_threshold
        else:
            score_threshold_query = None

        query_params.update(all_where_params)

        if len(query_vector) == 1536:
            vector_field = "vectors_1536"
            all_where_clauses.append("item.vectors_1536 is not null")
        elif len(query_vector) == 3072:
            vector_field = "vectors_3072"
            all_where_clauses.append("item.vectors_3072 is not null")
        else:
            raise ValueError("Query vector must be of length 1536 or 3072")

        if distance_function == "cosine":
            distance_query = f"1 - (item.{vector_field} <=> :vector) as similarity"
        elif distance_function == "inner_product":
            distance_query = f"(item.{vector_field} <#> :vector) * -1 as similarity"
        elif distance_function == "l1":
            distance_query = f"(item.{vector_field} <+> :vector) as similarity"
        elif distance_function == "l2":
            distance_query = f"1 - (item.{vector_field} <-> :vector) as similarity"
        else:
            raise ValueError("Invalid distance function")

        if randomize:
            order_by = "random()"
        else:
            order_by = "similarity_table.similarity desc"

        if sort:
            pagination_query = "limit :topn"
            query_params["topn"] = sort.topn
        else:
            pagination_query = "limit :limit offset :offset"
            query_params["topn"] = limit
            query_params["offset"] = offset

        query = text("""
           select id,external_id,similarity,scores from (
               select item.id,item.external_id,item.fields,item.scores, {distance_query} from item {where_clauses}
               ) as similarity_table {score_threshold_query} order by {order_by} {pagination_query}
        """.format(
            where_clauses=f"where {' and '.join(all_where_clauses)}" if all_where_clauses else "",
            order_by=order_by,
            topn=sort.topn if sort else limit,
            distance_query=distance_query,
            pagination_query=pagination_query,
            score_threshold_query=f"where {score_threshold_query}" if score_threshold_query else "",
        )).params(query_params)

        similar_items = self.db.execute(query).fetchall()

        similar_items = [SimilarItem(
            id=item.id,
            similarity=item.similarity,
            score=sort and item.scores.get(sort.score_name) or 0,
        ) for item in similar_items]

        if sort and similar_items:
            similar_items = self.sort_similar_items(
                similar_items,
                sort,
                limit,
                offset
            )

        items = Item.objects(self.db).filter(Item.id.in_([item.id for item in similar_items])).all()
        items_per_id = {item.id: item for item in items}

        recommendations = []
        for similar_item in similar_items:
            item = items_per_id[similar_item.id]
            recommendations.append(RecommendedItem(
                id=item.external_id,
                fields=item.fields,
                similarity=similar_item.similarity,
                score=similar_item.score
            ))

        return recommendations

    def get_query_vector_from_fields(self, fields) -> List[int]:
        description_hash = get_fields_hash(fields)
        matching_item = m.Item.objects(self.db).filter(m.Item.description_hash == description_hash).first()
        if matching_item:
            return matching_item.vector

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
            all_embeddings[item.id] = item.vector

        return all_embeddings


class SimilarItem(object):
    def __init__(self, id, similarity, score=None):
        self.id = id
        self.similarity = similarity
        self.score = score
