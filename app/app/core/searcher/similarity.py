from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Union

from app.core.searcher.queries.text_queries import TextQuery
from app.core.searcher.queries.vector_queries import VectorQuery
from app.models import Item, Collection
from app.utils.timeit import Timeit
from app.core.searcher.queries.query_parser import QueryParser
from app.core.searcher.types import SearchConfig, SearchItem, FilterQuery


class SimilarityEngine(object):
    def __init__(self, db: Session, collection: Collection):
        self.collection = collection
        self.db = db
        self.embeddings_calculator = collection.get_embeddings_calculator()

    def filter_out_ingested_items(self, items: List[Item]) -> List[Item]:
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

    def get_weighted_vectors(
        self, query_vectors: List[VectorQuery]
    ) -> List[List[float]]:
        weighted_vectors = []
        for vector_query in query_vectors:
            weighted_vectors.append(
                [i * vector_query.weight for i in vector_query.vector]
            )

        return weighted_vectors

    async def search(
        self, config: SearchConfig, exclude: List[str], context: dict
    ) -> List[SearchItem]:
        query_parser = QueryParser(
            self.db, collection=self.collection, context=context, queries=config.queries
        )

        vector_queries: List[VectorQuery] = query_parser.get_vectors()
        text_queries: List[TextQuery] = query_parser.get_text_queries()
        filter_queries: List[FilterQuery] = query_parser.get_filter_queries()

        if isinstance(config.filters, dict):
            filter_queries.append(FilterQuery(fields=config.filters))
        elif isinstance(config.filters, list):
            filter_queries.extend(config.filters)

        if config.filter:
            filter_queries.append(FilterQuery(fields=config.filter))

        return await self.get_similar(
            exclude_external_item_ids=exclude,
            vector_queries=vector_queries,
            text_queries=text_queries,
            filter_queries=filter_queries,
            limit=self.get_actual_limit_from_config(config),
            offset=config.offset,
            export=config.export,
            context=context,
        )

    def get_actual_limit_from_config(self, config):
        limit = config.limit
        if config.rank and config.rank.topn and config.rank.topn > limit:
            limit = config.rank.topn

        return limit

    def build_json_filters(self, filters):
        filters_dict = {}
        for filter in filters:
            filters_dict.update(filter.fields)
        return filters_dict

    async def get_similar(
        self,
        vector_queries: List[VectorQuery] = None,
        text_queries: List[TextQuery] = None,
        filter_queries: List[Union[FilterQuery]] = None,
        exclude_external_item_ids: List[Union[int, str]] = None,
        limit: int = 10,
        offset: int = 0,
        export: Union[str, List[str]] = None,
        context: dict = None,
    ):
        filters_dict = self.build_json_filters(filter_queries)

        if vector_queries:
            vector_queries = self.get_weighted_vectors(vector_queries)

            query_vector = self.get_average_vector_of_vectors(vector_queries)
        else:
            query_vector = None

        if text_queries:
            text_search_query = " ".join([query.text for query in text_queries])
        else:
            text_search_query = None

        min_score_threshold = (
            min([query.score_threshold for query in text_queries])
            if text_queries
            else 0
        )

        with Timeit("indexer.search"):
            similar_items = await self.collection.get_indexer().search(
                filters=filters_dict,
                text_search_query=text_search_query,
                vector=query_vector,
                limit=limit,
                score_threshold=min_score_threshold,
                offset=offset,
                exclude_external_ids=exclude_external_item_ids,
            )

        items = (
            Item.objects(self.db)
            .select(
                Item.id, Item.external_id, Item.fields, Item.scores, Item.description
            )
            .filter(Item.id.in_([item.id for item in similar_items]))
            .all()
        )

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
                    exported_value = {field: item.fields.get(field) for field in export}

            recommendations.append(
                SearchItem(
                    id=item.external_id,
                    fields=item.fields,
                    score=items_similarity[item.id],
                    scores=item.scores or {},
                    exported=exported_value if export is not None else None,
                    description=item.description,
                )
            )

        return recommendations

    def get_embeddings_of_items(self, items, skip_ingested=True):
        if skip_ingested:
            changed_items = self.filter_out_ingested_items(items)
        else:
            changed_items = items

        changed_item_embeddings = self.embeddings_calculator.get_embeddings_from_items(
            changed_items
        )

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
