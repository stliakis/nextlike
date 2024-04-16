from typing import List

import datetime
from app.recommender.embeddings import OpenAiEmbeddingsCalculator
from app.recommender.similarity_engine import SimilarityEngine
from app.recommender.types import SimpleItem
from app.resources.database import m
from app.settings import get_settings

from app.utils.logging import log
from app.db.base_class import ObjectBulkCreator
from app.models.collection import Collection
from app.models.recommendations.events.event import Event
from app.models.recommendations.items.item import Item
from app.models.recommendations.persons.person import Person


class EventsBulkCreator(ObjectBulkCreator):
    def create(self, collection_id, event_type, person_external_id, item_external_id, weight, item=None, person=None):
        return super(EventsBulkCreator, self).create(
            collection_id=collection_id,
            event_type=event_type,
            person_external_id=person_external_id,
            item_external_id=item_external_id,
            item=item,
            weight=weight,
            person=person,
        )

    def flush(self):
        collections = {}

        all_events = []

        all_related_recommendations = m.SearchHistory.objects(self.db).filter(
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

        items_to_recommendations = {}
        for recommendation in all_related_recommendations:
            for item in recommendation.external_item_ids:
                if item not in items_to_recommendations:
                    items_to_recommendations[item] = recommendation.id

        for obj in self.objects:
            event = Event().set(
                event_type=obj.get("event_type"),
                person_external_id=obj.get("person_external_id"),
                item_external_id=obj.get("item_external_id"),
                collection_id=obj.get("collection_id"),
                weight=obj.get("weight"),
                related_recommendation_id=items_to_recommendations.get(obj.get("item_external_id"))
            )

            self.db.add(event)

            if obj.get("person_external_id"):
                collections.setdefault(obj.get("collection_id"), {}).setdefault("persons", {}).setdefault(
                    obj.get("person_external_id"), {}).update(obj.get("person") or {})

            if obj.get("item_external_id"):
                collections.setdefault(obj.get("collection_id"), {}).setdefault("items", {}).setdefault(
                    obj.get("item_external_id"), {}).update(obj.get("item") or {})

            all_events.append(event)

        for collection_id, collection in collections.items():
            items = collection.get("items")
            persons = collection.get("persons")

            if items:
                ItemsBulkCreator(db=self.db).create_or_update(collection_id, items)

            if persons:
                PersonsBulkCreator(db=self.db).create_or_update(collection_id, persons)

        self.objects = []
        self.db.commit()
        self.db.flush()


class ItemsBulkCreator(ObjectBulkCreator):
    objects: List[SimpleItem]

    def __init__(self, recalculate_vectors=False, *args, **kwargs):
        super(ItemsBulkCreator, self).__init__(*args, **kwargs)
        self.recalculate_vectors = recalculate_vectors

    def create(self, collection: Collection, item: SimpleItem):
        self.objects.append((collection, item))
        self.flush_if_needed()
        return self

    def flush(self):
        per_collection = {}
        for collection, item in self.objects:
            per_collection.setdefault(collection, []).append(item)

        for collection, items in per_collection.items():
            self.create_or_update(collection, items)

        self.db.flush()
        self.objects = []

    def create_or_update(self, collection: Collection, items: List[SimpleItem]):
        from app.models.recommendations.items.items_field import ItemsField

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
            else:
                db_item = Item().set(
                    collection_id=collection.id,
                    external_id=item.id
                )
                db_item.update_from_simple_item(item)
                self.db.add(db_item)

            all_items.append(db_item)

        ItemsField.objects(self.db).create_fields_if_missing(collection, all_field_names)

        self.db.commit()
        self.db.flush()

        all_items_with_fields = [item for item in all_items if item.fields]

        similarity_engine = SimilarityEngine(self.db, collection,
                                             embeddings_calculator=OpenAiEmbeddingsCalculator())

        embeddings = similarity_engine.get_embeddings_of_items(all_items_with_fields,
                                                               skip_ingested=not self.recalculate_vectors)
        for item in all_items:
            item.vectors_1536 = embeddings.get(item.id)
            item.description_hash = item.get_hash()
            self.db.add(item)

        self.db.commit()
        self.db.flush()


class PersonsBulkCreator(ObjectBulkCreator):
    def create(self, collection_id, external_id, fields):
        self.objects.append({
            "collection_id": collection_id,
            "external_id": external_id,
            "fields": fields
        })
        self.flush_if_needed()
        return self

    def flush(self):
        per_project = {}
        for obj in self.objects:
            per_project.setdefault(obj.get("collection_id"), {}).setdefault(obj.get("external_id"), {}).update(
                obj.get("fields") or {})

        for collection_id, items in per_project.items():
            self.create_or_update(collection_id, items)

        self.db.flush()
        self.objects = []

    def create_or_update(self, collection_id, persons):
        existing_persons = Person.objects(self.db).filter(
            Person.collection_id == collection_id,
            Person.external_id.in_(persons.keys())
        )
        existing_persons = {
            i.external_id: i for i in existing_persons
        }

        from app.models.recommendations.persons.persons_fields import PersonsField

        all_field_names = {}

        for external_person_id, person in persons.items():
            for field_name, field_value in person.items():
                all_field_names.setdefault(field_name, []).append(PersonsField.find_best_fit_value_type_of_value(
                    field_value
                ))

            existing_person = existing_persons.get(external_person_id)
            if existing_person:
                existing_person.update_fields(person)
            else:
                self.db.add(Person().set(
                    collection_id=collection_id,
                    fields=person,
                    external_id=external_person_id
                ))

        PersonsField.objects(self.db).create_fields_if_missing(collection_id, all_field_names)

        self.db.commit()
        self.db.flush()
