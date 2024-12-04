from typing import List

from app.core.aggregator.aggregator import Aggregator
from app.core.searcher.searcher import Searcher
from app.core.types import Suggestion
from app.resources.database import m


class Suggestor(object):
    def __init__(self, organization, db, config):
        self.organization = organization
        self.db = db
        self.config = config

    def merge_suggestions(self, source, destination):
        for suggestion in source:
            existings = False
            for suggestion2 in destination:
                if suggestion.is_same(suggestion2):
                    existings = True
                    break

            if not existings:
                destination.append(suggestion)

        return destination

    async def suggest(self):
        suggestions = []

        if self.config.search:
            search_suggestions = await self.get_search_suggestions(self.config.search)
            suggestions = self.merge_suggestions(search_suggestions, suggestions)
        if self.config.aggregate and not len(suggestions) >= self.config.limit:
            aggregation_suggestions = await self.get_aggregate_suggestions(self.config.aggregate)
            suggestions = self.merge_suggestions(aggregation_suggestions, suggestions)

        suggestions = await self.rank_suggestions(suggestions)

        return suggestions[:self.config.limit]

    async def get_search_suggestions(self, search_config) -> List[Suggestion]:
        collection = m.Collection.objects(self.db).get_or_create(
            search_config.collection,
            self.organization
        )

        searcher = Searcher(
            db=self.db,
            collection=collection,
            config=search_config
        )

        result = await searcher.get_search_results()

        suggestions = []

        for item in result.items:
            suggestions.append(Suggestion(
                type="search",
                fields=item.fields,
                item_id=item.id,
                score=item.score
            ))

        return suggestions

    async def get_aggregate_suggestions(self, aggregate_config) -> List[Suggestion]:
        collection = m.Collection.objects(self.db).get_or_create(
            aggregate_config.collection,
            self.organization
        )

        aggregator = Aggregator(
            db=self.db,
            collection=collection,
            config=aggregate_config
        )

        result = await aggregator.aggregate()

        suggestions = []

        for aggregation in result:
            for item in aggregation.items:
                suggestions.append(Suggestion(
                    type="aggregation",
                    aggregation_name=aggregation.aggregation,
                    fields=item,
                    score=1
                ))

        return suggestions

    async def rank_suggestions(self, suggestions):
        return suggestions
