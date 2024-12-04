from app.easytests import EasyTest
from app.resources.database import m
from app.tests.config import nextlike_easytest_config
from app.tests.test_collections import TestCollectionConfig
from app.tests.test_items import TestItemCreation


class TestSearchSimilarApi(EasyTest):
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
            },
            {
                "collection": "test_collection2",
                "query": {
                    "prompt": "bmw",
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
            },
        ]

    async def test(self, collection, query, items, should_contain):
        await self.continue_with_test(TestCollectionConfig, {"collection": collection, "config": {
            "indexer": "redis",
            "embeddings_model": "text-embedding-3-small"
        }})
        await self.continue_with_test(TestItemCreation, {"collection": collection, "items": items})

        response = self.sync_request(
            "post",
            "/api/search",
            json={
                "collection": collection,
                "config": {
                    "similar": {
                        "of": [
                            query
                        ]
                    },
                    "cache": None
                }
            },
            expected_status=200
        )

        found_items = response.jstruct.items or []

        self.should("items contain id = 1", any(item.get("id") in should_contain for item in found_items))

        self.destroy_later("collection",
                           lambda: m.Collection.objects(self.db).delete_by_name(collection))
