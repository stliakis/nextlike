from app.easytests import EasyTest
from app.resources.database import m
from app.tests.config import nextlike_easytest_config
from app.tests.test_collections import TestCollectionFlow
from app.tests.test_items import TestItemCreation


class TestAggregationsApi(EasyTest):
    config = nextlike_easytest_config

    async def get_cases(self):
        return [
            {
                "collection": "test_collection",
                "collection_config": {
                    "indexer": "redis",
                    "embeddings_model": "text-embedding-3-small"
                },
                "should_contain": ["2"],
                "items": [
                    {
                        "id": "1",
                        "description": "bmw 316",
                        "fields": {
                            "make": "bmw"
                        }
                    },
                    {
                        "id": "2",
                        "fields": {
                            "make": "opel"
                        },
                        "description": "opel corsa"
                    },
                    {
                        "id": "3",
                        "fields": {
                            "field": "color",
                            "value": "_red_"
                        },
                        "description": "color red",
                        "description_preprocess": {
                            "prompt": "add synonym words for the text, greek words and make it suitable for text similarity"
                        }
                    },
                    {
                        "id": "4",
                        "fields": {
                            "field": "color",
                            "value": "_green_"
                        },
                        "description": "color green",
                        "description_preprocess": {
                            "prompt": "add synonym words for the text, greek words and make it suitable for text similarity"
                        }
                    }
                ],
                "similar_of": {
                    "prompt": "$query"
                }
            }
        ]

    async def test(self, collection, items, should_contain, similar_of, collection_config):
        await self.continue_with_test(TestCollectionFlow, {"collection": collection, "config": collection_config})
        await self.continue_with_test(TestItemCreation, {"collection": collection, "items": items})

        response = await self.request(
            "post",
            "/api/aggregate",
            json={
                "collection": collection,
                "config": {
                    "heavy_model": "openai:gpt-4o",
                    "prompt": "red opel corsa up to 3000 euros 2011-2016",
                    "aggregations": [
                        {
                            "name": "test_aggregation",
                            "fields": {
                                "make": {
                                    "type": "text",
                                    "description": "make of the car"
                                },
                                "model": {
                                    "type": "text",
                                    "description": "model of the car"
                                },
                                "year": {
                                    "type": "integer",
                                    "description": "year of the car"
                                },
                                "price_from": {
                                    "type": "integer",
                                    "description": "the minimum price"
                                },
                                "price_to": {
                                    "type": "integer",
                                    "description": "the maximum price"
                                },
                                "color": {
                                    "type": "item",
                                    "description": "color of the car",
                                    "search": {
                                        "similar": {
                                            "of": [
                                                similar_of
                                            ]
                                        },
                                        "filter": {
                                            "field": "color"
                                        },
                                        "export": "value",
                                        "cache": None,
                                        "limit": 1
                                    }
                                }
                            }
                        }
                    ]
                }
            },
            expected_status=200
        )

        self.should("have a response", response)
        self.should("have the correct aggregations", len(response.jstruct.aggregations), 1)
        self.should("have the correct aggregation name", response.jstruct.aggregations[0].aggregation,
                    "test_aggregation")

        aggregation = response.jstruct.aggregations[0]
        aggregation_items = aggregation.items

        self.should("have the correct make", aggregation_items[0].get("make").lower(), "opel")
        self.should("have the correct model", aggregation_items[0].get("model").lower(), "corsa")
        self.should("have the correct year", aggregation_items[0].get("year"), 2011)
        self.should("have the correct price_from", aggregation_items[0].get("price_to"), 3000)
        self.should("have the correct color", aggregation_items[0].get("color"), "_red_")
