from typing import List

from app.celery_app import celery_app
from app.db.session import Database
from app.models import Event
from app.models.collection import Collection
from app.models.search.bulk_creators import EventsBulkCreator
from app.core.types import SimpleEvent


@celery_app.task
def ingest_events(collection_id: int, events: List[SimpleEvent]):
    with Database() as db:
        collection = Collection.objects(db).get(collection_id)

        creator = EventsBulkCreator(db, bulk_size=5000, flush_after_seconds=30)
        for event in events:
            creator.create(
                collection_id=collection.id,
                event_type=event.event,
                person_external_id=event.person,
                item_external_id=event.item,
                date=event.date,
                weight=event.weight
            )
        creator.flush()


@celery_app.task
def cleanup_events(collection_id: int):
    with Database() as db:
        collection = Collection.objects(db).get(collection_id)
        Event.objects(db).filter(Event.collection_id == collection.id).delete()
