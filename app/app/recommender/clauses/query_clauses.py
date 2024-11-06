from logging import INFO, log
from typing import List, Tuple

from app.llm.llm import get_llm
from app.settings import get_settings


class QueryClause(object):
    def get_queries(self) -> List[Tuple[List[int], float]]:
        raise NotImplementedError


class QuerySearchClause(QueryClause):
    def __init__(self, db, similarity_engine, query: str, weight: float = 1.0, preprocess=None):
        self.db = db
        self.similarity_engine = similarity_engine
        self.query = query
        self.weight = weight
        self.preprocess = preprocess

    @classmethod
    def from_of(cls, db, similarity_engine, of):
        if hasattr(of, 'query'):
            return cls(db, similarity_engine, of.query, weight=of.weight, preprocess=of.preprocess)

    def preprocess_query(self, query):
        if self.preprocess:
            llm = get_llm(self.preprocess.model or get_settings().DEFAULT_LLM_PROVIDER_AND_MODEL)

            processed_query = llm.single_query(f"{self.preprocess.prompt}. The text is the following: '{query}'")

            log(INFO, f"processed prompt: {processed_query}")

            return processed_query
        else:
            return query

    def get_queries(self) -> List[Tuple[List[int], float]]:
        query = self.query

        query = self.preprocess_query(query)

        return [
            (query, self.weight)
        ]
