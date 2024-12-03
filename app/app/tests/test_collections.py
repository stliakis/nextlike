from app.easytests import EasyTest
from app.resources.database import m
from app.tests.config import nextlike_easytest_config


class TestCollectionFlow(EasyTest):
    config = nextlike_easytest_config

    async def get_cases(self) -> list[dict]:
        return [
            {
                "collection": "test_collection_flow",
                "config": {
                    "indexer": "postgres",
                    "embeddings_model": "text-embedding-3-small",
                }
            }
        ]

    async def test(self, collection, config):
        await self.request(
            "put",
            "/api/collections",
            json={
                "collection": collection,
                "config": config
            },
            expected_status=200
        )

        collection = m.Collection.objects(self.db).get_by_name(collection)

        self.should("have a collection", collection)
        self.should("have the correct indexer", collection.config.indexer, config.get("indexer"))
        self.should("have the correct embeddings model", collection.config.embeddings_model,
                    config.get("embeddings_model"))

        self.destroy_later("collection", lambda: collection.delete(self.db))


class TestCollectionConfig(EasyTest):
    config = nextlike_easytest_config

    async def get_cases(self) -> list[dict]:
        return [
            {
                "collection": "test_collection_config",
                "config": {
                    "indexer": "redis",
                    "embeddings_model": "text-embedding-3-small",
                }
            }
        ]

    async def test(self, collection, config):
        await self.request(
            "put",
            "/api/collections",
            json={
                "collection": collection,
                "config": config
            },
            expected_status=200
        )

        collection = m.Collection.objects(self.db).get_by_name(collection)

        self.should("have a collection", collection)
        self.should("have the correct indexer", collection.config.indexer, config.get("indexer"))
        self.should("have the correct embeddings model", collection.config.embeddings_model,
                    config.get("embeddings_model"))
