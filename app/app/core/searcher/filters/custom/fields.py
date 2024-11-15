from app.core.searcher.filters.custom.custom import CustomFilter
from app.core.types import SQLQueryCondition, FieldsFilterConfig
from app.models import Collection
from app.utils.base import listify


class FieldsFilter(CustomFilter):
    def __init__(self, db, collection: Collection, fields_column: str = "fields"):
        self.fields_column = fields_column
        self.db = db
        self.collection = collection

    @classmethod
    def is_valid(cls, filter):
        return 'fields' in filter or isinstance(filter, FieldsFilterConfig)

    async def apply(self, filter):
        return filter.fields
