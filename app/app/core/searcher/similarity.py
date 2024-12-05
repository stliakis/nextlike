import random

from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Union, Tuple
from app.core.searcher.filtered_engine import FilteredEngine
from app.exceptions.query_config import QueryConfigError
from app.models import Item, Collection
from app.core.searcher.clauses.base import get_vectors_from_ofs, get_text_queries_from_ofs
from app.core.types import SearchConfig, SearchItem, FilterQueryConfig, TextClauseQuery
from app.resources.database import m
from app.utils.base import get_fields_hash
from app.utils.timeit import Timeit


class SimilarityEngine(FilteredEngine):
    def __init__(self, db: Session, collection: Collection):
        self.collection = collection
        self.db = db
        self.embeddings_calculator = collection.get_embeddings_calculator()

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
        queries: List[TextClauseQuery] = []

        if config.similar:
            vectors.extend(get_vectors_from_ofs(self.db, self, config.similar.of, context))
            queries.extend(get_text_queries_from_ofs(self.db, self, config.similar.of, context))

        filters = config.filters
        if isinstance(filters, dict):
            filters = [FilterQueryConfig(fields=filters)]

        return await self.get_similar(
            query_vectors=vectors,
            exclude_external_item_ids=exclude,
            queries=queries,
            limit=self.get_actual_limit_from_config(config),
            offset=config.offset,
            filters=filters,
            export=config.export,
            context=context
        )

    def get_actual_limit_from_config(self, config):
        limit = config.limit
        if config.rank and config.rank.topn and config.rank.topn > limit:
            limit = config.rank.topn

        return limit

    async def get_similar(
            self,
            query_vectors: List[Tuple[List[int], float]] = None,
            exclude_external_item_ids: List[Union[int, str]] = None,
            queries: List[TextClauseQuery] = None,
            limit: int = 10,
            offset: int = 0,
            filters: List[Union[FilterQueryConfig]] = None,
            export: Union[str, List[str]] = None,
            context: dict = None
    ):
        filters_dict = await self.build_json_filters(filters)

        if query_vectors:
            query_vectors = self.get_weighted_vectors(query_vectors)

            query_vector = self.get_average_vector_of_vectors(query_vectors)
        else:
            query_vector = None

        if queries:
            text_search_query = " ".join([query.query for query in queries])
        else:
            text_search_query = None

        min_score_threshold = min([query.score_threshold for query in queries]) if queries else 0

        with Timeit("indexer.search"):
            similar_items = await self.collection.get_indexer().search(
                filters=filters_dict,
                text_search_query=text_search_query,
                vector=query_vector,
                limit=limit,
                score_threshold=min_score_threshold,
                offset=offset,
                exclude_external_ids=exclude_external_item_ids
            )

        items = Item.objects(self.db).select(Item.id, Item.external_id, Item.fields, Item.scores,
                                             Item.description).filter(
            Item.id.in_([item.id for item in similar_items])).all()

        items_similarity = {int(item.id): item.similarity for item in similar_items}

        items_per_id = {item.id: item for item in items}

        recommendations = []
        for similar_item in items:
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
                score=items_similarity[item.id],
                scores=item.scores or {},
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
        if not self.embeddings_calculator:
            raise QueryConfigError(
                "Can't set do a vector search query without embeddings model, set one in collection config")

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
    score: float = None
