import asyncio
from typing import List, Union

from app.celery_app import celery_app
from app.db.session import Database
from app.models import Item
from app.models.collection import Collection
from app.models.search.bulk_creators import ItemsBulkCreator
from app.core.types import SimpleItem
from app.resources.database import m


@celery_app.task
def ingest_items(
    collection_id: int, items: List[SimpleItem], recalculate_vectors: bool, refresh: bool = False
):
    async def execute():
        with Database() as db:
            collection = Collection.objects(db).get(collection_id)

            creator = ItemsBulkCreator(
                db=db,
                bulk_size=10000,
                flush_after_seconds=30,
                refresh=refresh,
            )

            for item in items:
                await creator.create(collection=collection, item=item)

            await creator.flush()

    asyncio.run(execute())


@celery_app.task
def delete_items(collection_id: int, external_ids: List[Union[str, int]]):
    async def execute():
        with Database() as db:
            collection = Collection.objects(db).get(collection_id)
            Item.objects(db).filter(
                m.Item.collection_id == collection.id,
                m.Item.external_id.in_(external_ids),
            ).delete()
            db.commit()
            db.flush()

    asyncio.run(execute())
