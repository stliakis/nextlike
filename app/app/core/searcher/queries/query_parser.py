from typing import Union, List, Tuple

from app.core.queries.filter_queries import FieldsFilterQuery
from app.core.queries.item_queries import ItemToItemsQuery, PersonItemsQuery, RecommendationsItemsQuery, ItemQuery
from app.core.queries.text_queries import TextSearchQuery
from app.core.queries.vector_queries import FieldsToVectorQuery, ItemToVectorQuery, PersonToVectorQuery, \
    PromptToVectorQuery, EmbeddingsQuery, VectorQuery


class QueryParser(object):
    query_handlers = [
        FieldsFilterQuery,
        ItemToItemsQuery,
        PersonItemsQuery,
        RecommendationsItemsQuery,
        TextSearchQuery,
        FieldsToVectorQuery,
        ItemToVectorQuery,
        PersonToVectorQuery,
        PromptToVectorQuery,
        EmbeddingsQuery
    ]

    def __init__(self, db, collection, context, queries):
        self.queries = queries
        self.context = context
        self.collection = collection
        self.db = db

    def get_vectors(self):
        vectors: List[VectorQuery] = []

        for query in self.queries:
            for query_handler in self.query_handlers:
                if getattr(query, query_handler.name, None):
                    handler = query_handler(self.db, self.collection, self.context, query)
                    vectors.extend(handler.get_vectors())

    def get_items(self):
        items: List[ItemQuery] = []

        for query in self.queries:
            for query_handler in self.query_handlers:
                if getattr(query, query_handler.name, None):
                    handler = query_handler(self.db, self.collection, self.context, query)
                    items.extend(handler.get_items())

        return items

    def get_text_queries(self):
        text_queries = []

        for query in self.queries:
            for query_handler in self.query_handlers:
                if getattr(query, query_handler.name, None):
                    handler = query_handler(self.db, self.collection, self.context, query)
                    text_queries.extend(handler.get_text_queries())

        return text_queries

    def get_filter_queries(self):
        filter_queries = []

        for query in self.queries:
            for query_handler in self.query_handlers:
                if getattr(query, query_handler.name, None):
                    handler = query_handler(self.db, self.collection, self.context, query)
                    filter_queries.extend(handler.get_filter_queries())

        return filter_queries
