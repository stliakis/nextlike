import json

from app.easytests import EasyTest
from app.resources.database import m
from app.tests.config import nextlike_easytest_config
from app.tests.resources.real_estate_search_dataset import RealEstateSearchDataset
from app.tests.test_collections import TestCollectionFlow
from app.tests.test_items import TestItemCreation


class TestAggregationsApi(EasyTest):
    config = nextlike_easytest_config

    async def get_cases(self):
        return [
            {
                "collection": "aggregations_test_collection",
                "collection_config": {
                    "indexer": "redis",
                    "embeddings_model": "text-embedding-3-small",
                },
                "items": RealEstateSearchDataset().get_aggregation_items(),
                "prompt": "apartment in Athens up to 500 euros per month, with autonomous heating, 2005 or later, 100-200 sqm",
                "expected_item": {
                    "area_to": 200,
                    "area_from": 100,
                    "construction_year": 2005,
                    "offertype": "rent",
                    "heating_type": "autonomous",
                    "location": "athens",
                    "category": "apartment",
                    "price_to": 500,
                },
            },
            {
                "collection": "aggregations_test_collection",
                "collection_config": {
                    "indexer": "redis",
                    "embeddings_model": "text-embedding-3-small",
                },
                "items": RealEstateSearchDataset().get_aggregation_items(),
                "prompt": " office space 200 sqm or larger, max 3k rent per month in thessaloniki",
                "expected_item": {
                    "category": "office",
                    "offertype": "rent",
                    "area_from": 200,
                    "location": "thessaloniki",
                    "price_to": 3000,
                },
            },
        ]

    async def test(self, collection, items, collection_config, prompt, expected_item):
        await self.continue_with_test(
            TestCollectionFlow, {"collection": collection, "config": collection_config}
        )
        await self.continue_with_test(
            TestItemCreation, {"collection": collection, "items": items}
        )

        response = await self.request(
            "post",
            "/api/aggregate",
            json={
                "collection": collection,
                "config": {
                    "heavy_model": "openai:gpt-4o",
                    "prompt": prompt,
                    "aggregations": [
                        RealEstateSearchDataset().get_aggregation_config()
                    ],
                },
            },
            expected_status=200,
        )

        self.should("have a response", response)
        self.should(
            "have the correct aggregations", len(response.jstruct.aggregations), 1
        )
        self.should(
            "have the correct aggregation name",
            response.jstruct.aggregations[0].aggregation,
            "test_aggregation",
        )

        self.interact()

        aggregation = response.jstruct.aggregations[0]
        aggregation_items = aggregation.items
        aggregation_item = aggregation_items[0]

        self.should(
            "have the correct item fields",
            json.dumps(expected_item, sort_keys=True)
            == json.dumps(dict(aggregation_item), sort_keys=True),
        )
