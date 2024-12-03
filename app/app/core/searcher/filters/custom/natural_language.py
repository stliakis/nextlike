from logging import INFO

from app.core.types import NaturalLanguageQueryFilterConfig
from app.llm.llm import get_llm
from app.models import Collection
from app.settings import get_settings
from app.utils.logging import log


class NaturalLanguageQueryFilter(object):
    def __init__(self,
                 db,
                 collection: Collection):
        self.db = db
        self.collection = collection
        self.preprocess = None

    @classmethod
    def is_valid(cls, filter):
        return 'query' in filter or isinstance(filter, NaturalLanguageQueryFilterConfig)

    async def apply(self, filter):
        return self.get_filters(filter.query)

    def preprocess_query(self, query):
        if self.preprocess:
            llm = get_llm(self.preprocess.model or get_settings().DEFAULT_LLM_PROVIDER_AND_MODEL)

            processed_query = llm.single_query(f"{self.preprocess.prompt}. The text is the following: '{query}'")

            log(INFO, f"processed prompt: {processed_query}")

            return processed_query
        else:
            return query

    def get_filters(self, filter):
        # llm = get_llm(filter.model or get_settings().DEFAULT_LLM_PROVIDER_AND_MODEL)
        #
        # await Aggregator(db, collection, query).aggregate()

        return {}
