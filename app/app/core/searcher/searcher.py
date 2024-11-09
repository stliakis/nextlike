from sqlalchemy.orm import Session
from typing import List, Union

from app.models import Collection
from app.core.searcher.clauses.base import get_item_ids_from_ofs
from app.core.searcher.collaboration import CollaborativeEngine
from app.llm.embeddings import OpenAiEmbeddingsCalculator
from app.core.searcher.similarity import SimilarityEngine
from app.core.types import SearchConfig, SearchResult
from app.resources.cache import get_cache
from app.resources.database import m
from app.utils.base import listify, stable_hash
from app.utils.logging import log


class Searcher(object):
    def __init__(
            self, db: Session, collection: Collection, config: SearchConfig
    ):
        self.collection = collection
        self.config = config
        self.db = db
        self.collaborative_engine = CollaborativeEngine(db, collection)
        self.similarity_engine = SimilarityEngine(
            db,
            collection,
            OpenAiEmbeddingsCalculator(model=self.collection.default_embeddings_model),
        )

    def get_exclude_items(self) -> List[Union[str, int]]:
        items_to_exclude = []

        if self.config.exclude:
            items_to_exclude.extend(
                listify(get_item_ids_from_ofs(self.db, self.config.exclude))
            )

        return items_to_exclude

    def log_search_history(self, external_person_id, search_result):
        item_ids = [item.id for item in search_result.items]
        return m.SearchHistory(
            external_person_id=external_person_id,
            external_item_ids=item_ids,
            search_config=self.config.dict(),
            collection=self.collection,
        ).flush(self.db)

    def get_cache_key(self):
        cache_key = self.config.cache.key or str(self.config.dict())
        return str(stable_hash(cache_key))

    def get_search_results(self):
        if self.config.cache and self.config.cache.expire:
            cache_key = self.get_cache_key()
            cached = get_cache().get(cache_key)
            if cached:
                log("info", f"returning search results from cache({cache_key})")
                return cached

        excluded = self.get_exclude_items()

        search_results = []

        if self.config.similar:
            search_results.extend(
                self.similarity_engine.search(self.config, exclude=excluded)
            )

        if len(search_results) < self.config.limit and self.config.collaborative:
            search_results.extend(
                self.collaborative_engine.search(self.config, exclude=excluded)
            )

        search_result = SearchResult(items=search_results)

        if self.config.cache and self.config.cache.expire:
            get_cache().set(
                self.get_cache_key(), search_result, self.config.cache.expire
            )

        return search_result

    def search(self) -> SearchResult:
        search_result = self.get_search_results()
        search_entry = self.log_search_history(self.config.for_person, search_result)
        search_result.id = search_entry.id
        return search_result