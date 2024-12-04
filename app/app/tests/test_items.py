from app.easytests import EasyTest, SequelEasyTest
from app.resources.database import m
from app.tests.config import nextlike_easytest_config


class TestItemsFlow(EasyTest):
    config = nextlike_easytest_config

    async def get_cases(self):
        return [
            {
                "collection": "items_test_collection",
                "items": [
                    {
                        "id": "1",
                        "fields": {
                            "make": "BMW",
                            "model": "X5",
                        },
                        "description": "BMW X5",
                    },
                    {
                        "id": "2",
                        "fields": {
                            "make": "Audi",
                            "model": "A4",
                        },
                        "description": "Audi A4",
                    },
                    {
                        "id": "3",
                        "fields": {
                            "make": "BMW",
                            "model": "X6",
                        },
                        "description": "BMW X6",
                    }
                ]
            },
        ]

    async def test(self, items, collection):
        await self.continue_with_test(TestItemCreation, {"collection": collection, "items": items})
        await self.continue_with_test(TestItemDeletion, {"collection": collection, "items": items})

        self.destroy_later("collection",
                           lambda: m.Collection.objects(self.db).delete_by_name(collection))


class TestItemCreation(SequelEasyTest):
    config = nextlike_easytest_config

    async def test(self, collection, items):
        response = await self.request(
            "post",
            "/api/items",
            json={
                "items": items,
                "collection": collection,
                "sync": True
            },
            expected_status=200
        )

        collection = m.Collection.objects(self.db).get_by_name(collection)

        db_items = collection.items

        self.should("db items be correct length", len(db_items) == len(items))

        for item in items:
            db_item = next(i for i in db_items if i.external_id == item["id"])

            self.should("fields be the same", db_item.fields == item["fields"])

            self.should("db item be correct", db_item is not None)

        await collection.get_indexer().recreate()


class TestItemDeletion(SequelEasyTest):
    config = nextlike_easytest_config

    async def test(self, collection, items):
        response = await self.request(
            "delete",
            "/api/items",
            json={
                "ids": [item["id"] for item in items],
                "collection": collection,
                "sync": True
            },
            expected_status=200
        )

        collection = m.Collection.objects(self.db).get_by_name(collection)

        for item in items:
            db_item = m.Item.objects(self.db).filter(
                m.Item.collection_id == collection.id,
                m.Item.external_id == item["id"]
            ).first()
            self.should("db item be deleted", not db_item)
