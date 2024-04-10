import datetime
import enum

import pymongo.collection

from app.utils.base import listify
from app.resources.mongo import get_mongo
from app.utils.logging import log


class LogType(enum.Enum):
    RAW = "raw"
    EVENT_SEND_ERROR = "event_send_error"
    ITEM_SEND_ERROR = "item_send_error"
    PERSON_SEND_ERROR = "person_send_error"
    RECOMMENDATION_ERROR_UNKNOWN_ITEM = "recommendation_error_unknown_item"
    RECOMMENDATION_ERROR_UNKNOWN_PERSON = "recommendation_error_unknown_person"
    NEW_ITEM = "new_item"
    NEW_PERSON = "new_person"
    NEW_EVENT = "new_event"
    RECOMMENDATION = "recommendation"


class StoredLogs(object):
    def __init__(self, organization: 'Organization' = None, collection: 'Collection' = None):
        self.organization = organization
        self.collection = collection

    def get_store(self) -> pymongo.collection.Collection:
        collection = get_mongo("main")["logs"]

        return collection

    def log(
            self,
            log_type: LogType,
            *logs,
    ):
        final_document = {
            "log_type": log_type.value,
            "created": datetime.datetime.utcnow()
        }

        all_log_objects = list(logs)
        if self.organization:
            all_log_objects.append(self.organization)

        if self.collection:
            all_log_objects.append(self.collection)

        for logged_object in all_log_objects:
            if isinstance(logged_object, dict):
                final_document.update(logged_object)
            elif hasattr(logged_object, "to_log_dict"):
                final_document.update(logged_object.to_log_dict())
            else:
                log("warning", "object {} has no to_log_dict method".format(logged_object))

        log("info", "logging StoredLog: {}".format(final_document))

        self.get_store().insert_one(final_document)

    def get_default_filters(self):
        filters = {}
        if self.organization:
            filters["organization_id"] = self.organization.id

        if self.collection:
            filters["collection_id"] = self.collection.id
        return filters

    def delete_all_logs(self, **filters):
        filters = dict(self.get_default_filters(), **filters)
        self.get_store().delete_many(filters)

    def count_logs(self, **filters):
        filters = dict(self.get_default_filters(), **filters)
        return self.get_store().count_documents(filters)

    def get_logs(self, size=50, types=None, **filters):
        filters = dict(self.get_default_filters(), **filters)

        if types:
            filters["log_type"] = {
                "$in": listify(types)
            }

        return self.get_store().find(filters).limit(size).sort("created",
                                                               pymongo.DESCENDING)
