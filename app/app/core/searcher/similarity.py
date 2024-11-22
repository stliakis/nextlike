import random

from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Union, Tuple, Dict
from app.core.searcher.filtered_engine import FilteredEngine
from app.models import Item, Collection
from app.core.searcher.clauses.base import get_vectors_from_ofs, get_queries_from_ofs
from app.llm.embeddings import OpenAiEmbeddingsCalculator
from app.core.types import SearchConfig, SortingModifier, SearchItem, SQLQueryCondition, FilterQueryConfig
from app.resources.database import m
from app.utils.base import get_fields_hash
from app.utils.timeit import Timeit


class SimilarityEngine(FilteredEngine):
    def __init__(self, db: Session, collection: Collection, embeddings_calculator=None):
        self.collection = collection
        self.db = db
        self.embeddings_calculator = embeddings_calculator or OpenAiEmbeddingsCalculator(
            model=collection.default_embeddings_model)

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

    async def search(self, config: SearchConfig, exclude: List[str], context: dict) -> List[SearchItem]:
        vectors: List[Tuple[List[int], float]] = []
        queries: List[Tuple[str, float]] = []

        if config.similar:
            vectors.extend(get_vectors_from_ofs(self.db, self, config.similar.of, context))
            queries.extend(get_queries_from_ofs(self.db, self, config.similar.of, context))

        filters = config.filters
        if isinstance(filters, dict):
            filters = [FilterQueryConfig(fields=filters)]

        return await self.get_similar(
            query_vectors=vectors,
            exclude_external_item_ids=exclude,
            queries=queries,
            limit=config.limit,
            offset=config.offset,
            sort=config.similar and config.similar.sort,
            filters=filters,
            score_threshold=config.similar and config.similar.score_threshold,
            distance_function=config.similar and config.similar.distance_function,
            randomize=config.randomize,
            export=config.export,
            context=context
        )

    def sort_similar_items(self, similar_items, sort, limit, offset):
        if not similar_items:
            return []

        max_similarity = max(item.similarity for item in similar_items)
        min_similarity = min(item.similarity for item in similar_items)
        max_score = max(item.score for item in similar_items)
        min_score = min(item.score for item in similar_items)

        # Calculate ranges to avoid division by zero
        similarity_range = max_similarity - min_similarity if max_similarity != min_similarity else 1
        score_range = max_score - min_score if max_score != min_score else 1

        # Normalize similarity and score, then calculate final combined score
        for similar_item in similar_items:
            # Option 1: Min-Max Normalization with Cap
            normalized_similarity = (similar_item.similarity - min_similarity) / similarity_range
            normalized_similarity = min(normalized_similarity, 0.95)  # Cap to reduce the impact of outliers

            # Option 2: Logarithmic Normalization
            # normalized_similarity = math.log1p(similar_item.similarity - min_similarity) / math.log1p(similarity_range)

            normalized_score = (similar_item.score - min_score) / score_range

            # Combined score with normalized similarity and score weighted
            similar_item.score = (normalized_similarity * (1 - sort.weight) +
                                  normalized_score * sort.weight)

        # Sort by combined score in descending order and paginate
        sorted_items = sorted(similar_items, key=lambda x: x.score, reverse=True)
        paginated_items = sorted_items[offset:offset + limit]

        return paginated_items

    async def get_similar(
            self,
            query_vectors: List[Tuple[List[int], float]] = None,
            exclude_external_item_ids: List[Union[int, str]] = None,
            queries: List[Tuple[str, float]] = None,
            limit: int = 10,
            offset: int = 0,
            filters: List[Union[FilterQueryConfig]] = None,
            sort: SortingModifier = None,
            score_threshold: float = 0,
            distance_function: str = None,
            randomize: bool = False,
            randomize_topn: int = 100,
            export: Union[str, List[str]] = None,
            context: dict = None
    ):
        filters_dict = await self.build_json_filters(filters)

        query_limit = limit

        if sort:
            query_limit = sort.topn

        if randomize:
            query_limit = randomize_topn

        if query_vectors:
            query_vectors = self.get_weighted_vectors(query_vectors)

            query_vector = self.get_average_vector_of_vectors(query_vectors)
        else:
            query_vector = None

        if queries:
            text_search_query = " ".join([query[0] for query in queries])
        else:
            text_search_query = None

        with Timeit("indexer.search"):
            similar_items = await self.collection.get_indexer().search(
                filters=filters_dict,
                text_search_query=text_search_query,
                text_search_similarity_function=distance_function,
                vector=query_vector,
                limit=query_limit,
                offset=offset,
                exclude_external_ids=exclude_external_item_ids
            )

            print("similar:", similar_items)

        if randomize:
            random.shuffle(similar_items)

        similar_items = [item for item in similar_items if item.similarity >= score_threshold]

        items = Item.objects(self.db).select(Item.id, Item.external_id, Item.fields, Item.scores,
                                             Item.description).filter(
            Item.id.in_([item.id for item in similar_items])).all()

        items_similarity = {int(item.id): item.similarity for item in similar_items}

        similar_items = []
        for item in items:
            if item.id not in items_similarity:
                continue

            similarity = items_similarity[item.id]

            if sort:
                if not item.scores or not item.scores.get(sort.score_name):
                    score = 0
                else:
                    score = item.scores.get(sort.score_name)
            else:
                score = items_similarity[item.id]

            similar_items.append(SimilarItem(
                id=int(item.id),
                similarity=similarity,
                score=score
            ))

        if sort and similar_items:
            similar_items = self.sort_similar_items(
                similar_items,
                sort,
                limit,
                offset
            )

        similar_items = similar_items[:limit]

        items_per_id = {item.id: item for item in items}

        recommendations = []
        for similar_item in similar_items:
            item = items_per_id[similar_item.id]

            if export is None:
                exported_value = item.fields
            else:
                if isinstance(export, str):
                    exported_value = item.fields.get(export)
                else:
                    exported_value = {
                        field: item.fields.get(field) for field in export
                    }

            recommendations.append(SearchItem(
                id=item.external_id,
                fields=item.fields,
                similarity=similar_item.similarity,
                score=similar_item.score,
                exported=exported_value if export is not None else None,
                description=item.description
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


class SimilarItem(BaseModel):
    id: int
    similarity: float
    score: float = None
