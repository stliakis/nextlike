import asyncio

from app.celery_app import celery_app
from app.db.session import Database
from app.models import Collection
from app.resources.database import m
from app.utils.base import all_query_per_chunk
from sqlalchemy import text, or_

from app.utils.logging import log
from app.utils.temporal_lock import RedisTemporalLock


@celery_app.task
def maintain_collection(collection_id: int):
    async def execute():
        async with RedisTemporalLock(f"maintain-collection:{collection_id}", expire=3600 * 12) as unlocked:
            if unlocked:
                with Database() as db:
                    collection = Collection.objects(db).get(collection_id)

                    if collection.is_index_dirty:
                        await collection.get_indexer().recreate()
                        collection.is_index_dirty = False
                        collection.flush()

                    for chunk in all_query_per_chunk(
                            m.Item.objects(db).filter(m.Item.collection_id == collection.id,
                                                      or_(m.Item.is_index_dirty == True,
                                                          m.Item.is_embeddings_dirty == True)), 500):
                        await m.Collection.objects(db).refresh_items(collection, chunk)
                        log("info", "Beat.clean_dirty_items: Cleaned %i dirty items" % len(chunk))

    asyncio.run(execute())
