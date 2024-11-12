from logging import INFO, log
from typing import List, Tuple

from app.llm.llm import get_llm
from app.settings import get_settings
from app.utils.base import replace_variables_in_string


class TextClause(object):
    def get_queries(self) -> List[Tuple[List[int], float]]:
        raise NotImplementedError


class TextSearchClause(TextClause):
    def __init__(self, db, similarity_engine, query: str, weight: float = 1.0, distance_function: str = None,
                 preprocess=None):
        self.db = db
        self.similarity_engine = similarity_engine
        self.query = query
        self.weight = weight
        self.preprocess = preprocess
        self.distance_function = distance_function

    @classmethod
    def from_of(cls, db, similarity_engine, of, context):
        if hasattr(of, 'text'):
            return cls(db, similarity_engine, replace_variables_in_string(of.text, context), weight=of.weight,
                       preprocess=of.preprocess,
                       distance_function=of.distance_function)

    def preprocess_query(self, query):
        if self.preprocess:
            llm = get_llm(self.preprocess.model or get_settings().DEFAULT_LLM_PROVIDER_AND_MODEL)

            processed_query = llm.single_query(f"{self.preprocess.prompt}. The text is the following: '{query}'")

            log(INFO, f"processed prompt: {processed_query}")

            return processed_query
        else:
            return query

    def get_queries(self) -> List[Tuple[List[int], float, str]]:
        query = self.query

        query = self.preprocess_query(query)

        return [
            (query, self.weight, self.distance_function)
        ]
