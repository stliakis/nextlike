from typing import List

from app.core.indexers.types import IndexerResultItem


class Indexer(object):
    def __init__(self, db, collection):
        self.db = db
        self.collection = collection

    def search(self, filters=None,
               text_search_query=None,
               text_search_similarity_function="DOCSCORE",
               vector=None,
               limit=10,
               score_threshold=0,
               offset=0,
               exclude_external_ids=None) -> List[IndexerResultItem]:
        raise NotImplementedError()

    def cleanup(self):
        raise NotImplementedError()

    def recreate(self):
        raise NotImplementedError()

    @classmethod
    async def cleanup_all(cls, db):
        raise NotImplementedError()
