from typing import List, Tuple

import datetime
from app.core.types import SimpleItem, SimplePerson
from app.resources.database import m
from app.settings import get_settings
from app.db.base_class import ObjectBulkCreator
from app.models.collection import Collection
from app.models.search.events.event import Event
from app.models.search.items.item import Item
from app.models.search.persons.person import Person


class EventsBulkCreator(ObjectBulkCreator):
    async def create(self, collection_id, event_type, person_external_id, item_external_id, date, weight, item=None,
                     person=None):
        return super(EventsBulkCreator, self).create(
            collection_id=collection_id,
            event_type=event_type,
            person_external_id=person_external_id,
            item_external_id=item_external_id,
            item=item,
            date=date,
            weight=weight,
            person=person,
        )

    async def flush(self):
        collections = {}

        all_events = []

        all_related_searches = m.SearchHistory.objects(self.db).filter(
            m.SearchHistory.collection_id.in_(
                [obj.get("collection_id") for obj in self.objects]
            ),
            m.SearchHistory.external_person_id.in_(
                [obj.get("person_external_id") for obj in self.objects]
            ),
            m.SearchHistory.external_item_ids.contains(
                [obj.get("item_external_id") for obj in self.objects]
            ),
            m.SearchHistory.created > datetime.datetime.now() - datetime.timedelta(
                minutes=get_settings().EVENT_TO_RECOMMENDATION_HISTORY_THRESHOLD_MINUTES)
        ).order_by(m.SearchHistory.created.desc()).all()

        items_to_searches = {}
        for recommendation in all_related_searches:
            for item in recommendation.external_item_ids:
                if item not in items_to_searches:
                    items_to_searches[item] = recommendation.id

        for obj in self.objects:
            event = Event().set(
                event_type=obj.get("event_type"),
                person_external_id=obj.get("person_external_id"),
                item_external_id=obj.get("item_external_id"),
                collection_id=obj.get("collection_id"),
                weight=obj.get("weight"),
                created=obj.get("date"),
                related_recommendation_id=items_to_searches.get(obj.get("item_external_id"))
            )

            self.db.add(event)

            if obj.get("person_external_id"):
                collections.setdefault(obj.get("collection_id"), {}).setdefault("persons", []).append(
                    obj.get("person_external_id") or {}
                )

            if obj.get("item_external_id"):
                collections.setdefault(obj.get("collection_id"), {}).setdefault("items", []).append(
                    obj.get("item_external_id") or {}
                )

            all_events.append(event)

        for collection_id, collection in collections.items():
            items = collection.get("items")
            persons = collection.get("persons")

            collection = Collection.objects(self.db).get(collection_id)

            if items:
                await ItemsBulkCreator(db=self.db).create_or_update(collection, [
                    SimpleItem(id=item) for item in items
                ])

            if persons:
                await PersonsBulkCreator(db=self.db).create_or_update(collection.id, [
                    SimplePerson(id=person) for person in persons
                ])

        self.objects = []
        self.db.commit()
        self.db.flush()


class ItemsBulkCreator(ObjectBulkCreator):
    objects: List[Tuple[Collection, SimpleItem]]

    def __init__(self, recalculate_vectors=False, refresh=False, *args, **kwargs):
        super(ItemsBulkCreator, self).__init__(*args, **kwargs)
        self.recalculate_vectors = recalculate_vectors
        self.refresh = refresh

    async def create(self, collection: Collection, item: SimpleItem):
        self.objects.append((collection, item))
        await self.flush_if_needed()
        return self

    async def flush(self):
        per_collection = {}

        for collection, item in self.objects:
            per_collection.setdefault(collection, []).append(item)

        for collection, items in per_collection.items():
            await self.create_or_update(collection, items)

        self.db.flush()
        self.objects = []

    async def create_or_update(self, collection: Collection, items: List[SimpleItem]):
        from app.models.search.items.items_field import ItemsField

        existing_items = Item.objects(self.db).filter(
            Item.collection_id == collection.id,
            Item.external_id.in_([item.id for item in items])
        )

        existing_items = {
            i.external_id: i for i in existing_items
        }

        all_field_names = {}

        all_items = []
        for item in items:
            for field_name, field_value in item.fields.items():
                all_field_names.setdefault(field_name, []).append(ItemsField.find_best_fit_value_type_of_value(
                    field_value
                ))

            db_item = existing_items.get(item.id)
            if db_item:
                db_item.update_from_simple_item(item)
                old_description_hash = db_item.description_hash
                db_item.description_hash = db_item.get_hash()

                if db_item.description_hash != old_description_hash:
                    db_item.is_index_dirty = True
                    db_item.is_embeddings_dirty = True
                else:
                    db_item.is_index_dirty = True
            else:
                db_item = Item().set(
                    collection_id=collection.id,
                    external_id=item.id,
                    scores=item.scores or {},
                    is_index_dirty=True,
                    is_embeddings_dirty=True,
                )
                db_item.update_from_simple_item(item)
                db_item.description_hash = item.get_hash()
                self.db.add(db_item)

            all_items.append(db_item)

        if self.refresh:
            await m.Collection.objects(self.db).refresh_items(collection, all_items)

        ItemsField.objects(self.db).create_fields_if_missing(collection, all_field_names)

        self.db.commit()
        self.db.flush()


class PersonsBulkCreator(ObjectBulkCreator):
    async def create(self, collection_id, external_id, fields):
        self.objects.append({
            "collection_id": collection_id,
            "external_id": external_id,
            "fields": fields
        })
        await self.flush_if_needed()
        return self

    async def flush(self):
        per_project = {}
        for obj in self.objects:
            per_project.setdefault(obj.get("collection_id"), {}).setdefault(obj.get("external_id"), {}).update(
                obj.get("fields") or {})

        for collection_id, items in per_project.items():
            await self.create_or_update(collection_id, items)

        self.db.flush()
        self.objects = []

    async def create_or_update(self, collection_id, persons: List[SimplePerson]):
        persons_external_ids = [person.id for person in persons]

        existing_persons = Person.objects(self.db).filter(
            Person.collection_id == collection_id,
            Person.external_id.in_(persons_external_ids)
        )
        existing_persons = {
            i.external_id: i for i in existing_persons
        }

        from app.models.search.persons.persons_fields import PersonsField

        all_field_names = {}

        for person in persons:
            if person.fields:
                for field_name, field_value in person.fields.items():
                    all_field_names.setdefault(field_name, []).append(PersonsField.find_best_fit_value_type_of_value(
                        field_value
                    ))

            db_person = existing_persons.get(person.id)
            if db_person:
                db_person.update_from_simple_person(person)
            else:
                db_person = Person().set(
                    collection_id=collection_id,
                    external_id=person.id
                )
                db_person.update_from_simple_person(person)
                self.db.add(db_person)

        PersonsField.objects(self.db).create_fields_if_missing(collection_id, all_field_names)

        self.db.commit()
        self.db.flush()
