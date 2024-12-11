from logging import INFO, log
from typing import List, Tuple

from app.core.queries.base import BaseQuery
from app.core.types import TextQuery
from app.llm.llm import get_llm
from app.settings import get_settings
from pydantic.main import BaseModel


class TextSearchQuery(BaseQuery):
    name = "text"

    class Config(BaseModel):
        query: str
        weight: float = 1.0
        distance_function: str = None
        preprocess: str = None
        score_threshold: float = None

    def __init__(
            self,
            db,
            collection,
            context,
            config
    ):
        self.db = db
        self.collection = collection
        self.query = config.query
        self.weight = config.weight
        self.score_threshold = config.score_threshold
        self.preprocess = config.preprocess
        self.distance_function = config.distance_function
        self.context = context

    def preprocess_query(self, query):
        if self.preprocess:
            llm = get_llm(
                self.preprocess.model or get_settings().DEFAULT_LLM_PROVIDER_AND_MODEL
            )

            processed_query = llm.single_query(
                f"{self.preprocess.prompt}. The text is the following: '{query}'"
            )

            log(INFO, f"processed prompt: {processed_query}")

            return processed_query
        else:
            return query

    def get_text_queries(self) -> List[TextQuery]:
        query = self.query

        query = self.preprocess_query(query)

        return [
            TextQuery(
                query=query,
                weight=self.weight,
                distance_function=self.distance_function,
                score_threshold=self.score_threshold,
            )
        ]
