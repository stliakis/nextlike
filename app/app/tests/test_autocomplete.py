import json

from app.easytests import EasyTest
from app.tests.config import nextlike_easytest_config
from app.tests.resources.real_estate_search_dataset import RealEstateSearchDataset
from app.tests.test_collections import TestCollectionFlow
from app.tests.test_items import TestItemCreation


class TestAutocomplete(EasyTest):
    config = nextlike_easytest_config

    async def get_cases(self):
        return [
            {
                "query_items": RealEstateSearchDataset().get_query_items(),
                "query": "διαμ",
                "expected": [
                    {
                        "type": "aggregation",
                        "id": None,
                        "aggregation_name": "test_aggregation",
                        "item_id": None,
                        "fields": {
                            "category": "apartment",
                            "tags": "sea_view",
                            "location": "athens"
                        },
                        "score": 1.0
                    }
                ]
            },
            {
                "query_items": RealEstateSearchDataset().get_query_items(),
                "query": "διαμ",
                "expected": [
                    {
                        "type": "search",
                        "id": None,
                        "aggregation_name": None,
                        "item_id": "query_apartment_athens",
                        "fields": {
                            "category": "apartment",
                            "location": "athens"
                        },
                        "score": 3.846153722712278
                    }
                ]
            }
        ]

    async def test(self, query_items, query, expected):
        await self.continue_with_test(TestCollectionFlow, {"collection": "test_search_bar:queries", "config": {
            "indexer": "redis",
            "embeddings_model": "text-embedding-3-small"
        }, "dont_teardown": True})
        await self.continue_with_test(TestItemCreation, {"collection": "test_search_bar:queries", "items": query_items})

        response = self.sync_request(
            "post",
            "/api/autocomplete",
            json={
                "collection": "test_search_bar:queries",
                "config": {
                    "model": "groq:mixtral-8x7b-32768",
                    "extra_info": "suggest only items valid for a classifieds website",
                    "query": query,
                    "contexts": [
                        {
                            "type": "items",
                            "collection": "test_search_bar:user_history",
                            "context_title": "recent user searches",
                            "search": {
                                "similar": {
                                    "of": []
                                },
                                "rank": {
                                    "score_function": "score + score.popularity * 0.5",
                                    "topn": 20
                                }
                            }
                        }
                    ]
                }
            },
            expected_status=200
        )

        # self.interact()

        # items = [dict(i) for i in response.jstruct.suggestions]
        #
        # for i in range(len(items)):
        #     item1 = items[i]
        #     item2 = expected[i]
        #
        #     self.should("type be correct", item1["type"] == item2["type"])
        #     self.should("id be correct", item1["id"] == item2["id"])
        #     self.should("aggregation_name be correct", item1["aggregation_name"] == item2["aggregation_name"])
        #     self.should("item_id be correct", item1["item_id"] == item2["item_id"])
        #     self.should("fields be correct", item1["fields"] == item2["fields"])
