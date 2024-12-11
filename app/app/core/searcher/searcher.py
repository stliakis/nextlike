import json
from sqlalchemy.orm import Session
from typing import List, Union

from app.core.searcher.queries.filter_queries import FilterQuery
from app.core.searcher.rankers import RandomRanker, ScoreRanker
from app.core.searcher.types import SearchConfig, SearchResult, SearchItem
from app.models import Collection
from app.core.searcher.similarity import SimilarityEngine
from app.resources.cache import get_cache
from app.resources.database import m
from app.utils.base import stable_hash
from app.utils.logging import log


class Searcher(object):
    def __init__(
        self,
        db: Session,
        collection: Collection,
        config: SearchConfig,
        precalculated_embeddings=None,
        context=None,
    ):
        self.collection = collection
        self.config = config
        self.db = db
        self.precalculated_embeddings = precalculated_embeddings or {}
        self.context = context or {}
        self.similarity_engine = SimilarityEngine(
            db,
            collection,
        )

    def get_exclude_items(self) -> List[Union[str, int]]:
        items_to_exclude = []

        # if self.config.exclude:
        #     items_to_exclude.extend(
        #         listify(get_item_ids_from_ofs(self.db, self.config.exclude, self.context))
        #     )

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
        cache_key = self.config.cache.key or (
            str(self.collection.id)
            + str(json.dumps(self.config.dict(), sort_keys=True))
            + str(json.dumps(self.context, sort_keys=True))
        )
        return str(stable_hash(cache_key))

    async def get_search_results(self) -> SearchResult:
        if self.config.cache and self.config.cache.expire:
            cache_key = self.get_cache_key()
            cached = get_cache().get(cache_key)

            if cached:
                log("info", f"returning search results from cache({cache_key})")
                return cached

        excluded = self.get_exclude_items()

        if self.config.filter:
            self.config.filters.append(FilterQuery(fields=self.config.filter))

        search_results: List[SearchItem] = await self.similarity_engine.search(
            self.config, exclude=excluded, context=self.context
        )

        if self.config.rank and self.config.rank.randomize:
            ranker = RandomRanker()
        elif self.config.rank and self.config.rank.score_function:
            ranker = ScoreRanker(self.config.rank.score_function)
        else:
            ranker = ScoreRanker("score")

        search_results = ranker.rank(search_results, self.config.limit)

        search_result = SearchResult(items=search_results)

        if self.config.cache and self.config.cache.expire:
            get_cache().set(
                self.get_cache_key(), search_result, self.config.cache.expire
            )

        return search_result

    async def search(self) -> SearchResult:
        search_result = await self.get_search_results()
        search_entry = self.log_search_history(self.config.for_person, search_result)
        search_result.id = search_entry.id
        return search_result
