from pprint import pprint
from typing import List

from requests import Session

from app.core.searcher.rankers import ScoreRanker
from app.core.searcher.searcher import Searcher
from app.core.suggestor.context_providers import ContextProvider
from app.core.suggestor.llm_suggestions import LLMSuggestions
from app.core.types import AutoCompleteConfig, SearchItem, SearchConfig, SimilaritySearchConfig, \
    TextClausePrompt, SearchRankConfig
from app.models import Collection


class AutoCompletor():
    def __init__(self, db: Session, collection: Collection, config: AutoCompleteConfig):
        self.collection = collection
        self.config = config
        self.db = db

    async def autocomplete(self):
        context_providers = []
        for context in self.config.contexts:
            provider = ContextProvider.get_provider(self.db, self.collection, context)
            if provider:
                context_providers.append(provider)

        llm_suggestions = LLMSuggestions(self.db, self.collection, contexts=context_providers,
                                         extra_info=self.config.extra_info, model=self.config.model)

        items = llm_suggestions.get_items(query=self.config.query)

        valid_items: List[SearchItem] = []

        print()

        print("got:", len(items))

        added_items = set()
        for text_item in items:
            searcher = Searcher(
                db=self.db,
                collection=self.collection,
                config=SearchConfig(
                    similar=SimilaritySearchConfig(
                        of=[
                            TextClausePrompt(
                                text=text_item,
                            )
                        ]
                    ),
                    rank=SearchRankConfig(
                        topn=20,
                        score_function="score + score.popularity * 0.5"
                    ),
                    limit=1,
                    cache=None
                )
            )

            print("searching for:", text_item)
            results = await searcher.get_search_results()
            print("results:", results.items)

            for item in results.items:
                if item.id in added_items:
                    continue

                valid_items.append(item)
                added_items.add(item.id)

        return valid_items
