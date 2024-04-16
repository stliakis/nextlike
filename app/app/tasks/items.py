from typing import List, Union

from app.celery_app import celery_app
from app.db.session import Database
from app.models import Item
from app.models.collection import Collection
from app.models.recommendations.bulk_creators import ItemsBulkCreator
from app.recommender.types import SimpleItem


@celery_app.task
def ingest_items(collection_id: int, items: List[SimpleItem], recalculate_vectors: bool):
    with Database() as db:
        collection = Collection.objects(db).get(collection_id)

        creator = ItemsBulkCreator(db=db, bulk_size=10000, flush_after_seconds=30,
                                   recalculate_vectors=recalculate_vectors)
        for item in items:
            creator.create(
                collection=collection,
                item=item
            )

        creator.flush()


@celery_app.task
def delete_items(collection_id: int, external_ids: List[Union[str, int]]):
    with Database() as db:
        collection = Collection.objects(db).get(collection_id)
        Item.objects(db).filter(Item.collection_id == collection.id, Item.external_id.in_(external_ids)).delete()
