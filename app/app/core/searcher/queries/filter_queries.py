from typing import Union

from app.core.types import FilterQueryConfig
from pydantic.main import BaseModel


class FilterQuery(BaseModel):
    fields: dict[str, Union[str, int, None, bool, float]]


class FieldsFilterQuery(object):
    name = "filter"

    class Config(BaseModel):
        fields: dict[str, Union[str, int, None, bool, float]]

    def __init__(self, db, collection, context, config):
        self.db = db
        self.collection = collection
        self.fields = config.fields
        self.context = context

    def get_filter_queries(self):
        return FilterQuery(fields=self.fields)
