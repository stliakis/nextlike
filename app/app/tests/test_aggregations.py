from app.easytests import EasyTest
from app.resources.database import m
from app.tests.config import nextlike_easytest_config
from app.tests.test_items import TestItemCreation


class TestAggregationsApi(EasyTest):
    config = nextlike_easytest_config

    async def get_cases(self):
        return [
            {
                "collection": "test_collection",
                "query": {
                    "text": "opel corsa",
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
                    }
                ]
            }
        ]

    async def test(self, collection, query, items, should_contain):
        response = await self.request(
            "post",
            "/api/aggregate",
            json={
                "collection": collection,
                "config": {
                    "prompt": "opel corsa of year 2016",
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

        self.should("have the correct make", aggregation_items[0].get("make"), "opel")
        self.should("have the correct model", aggregation_items[0].get("model"), "corsa")
        self.should("have the correct year", aggregation_items[0].get("year"), 2016)

        self.interact()
