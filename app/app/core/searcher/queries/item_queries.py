from typing import Union, List, Tuple

from sqlalchemy import text

from app.core.helpers import get_external_item_ids_of_events_for_user
from app.core.queries.base import BaseQuery
from app.utils.base import listify, time_string_to_datetime_from_now
from pydantic.main import BaseModel


class ItemQuery(BaseModel):
    item: Union[List[str], str]
    weight: float = 1.0


class ItemToItemsQuery(BaseQuery):
    name = "items_to_items"

    class Config(BaseModel):
        item: Union[List[str], str]
        weight: float = 1.0

    def __init__(self, db, collection, context, config):
        self.db = db
        self.collection = collection
        self.context = context
        self.item = config.item
        self.weight = config.weight

    def get_items(self) -> List[ItemQuery]:
        items = listify(self.item)
        return [ItemQuery(item=item, weight=self.weight) for item in items]


class PersonItemsQuery(BaseQuery):
    name = "person_to_items"

    class Config(BaseModel):
        person: Union[List[str], str]
        weight: float = 1.0
        limit: int = 10
        time: str = "1M"

    def __init__(self, db, collection, context, config):
        self.db = db
        self.collection = collection
        self.context = context
        self.person = config.person
        self.weight = config.weight
        self.time = config.time
        self.limit = config.limit

    def get_items(self) -> List[ItemQuery]:
        vectors_person_interacted_with = get_external_item_ids_of_events_for_user(
            db=self.db,
            external_person_ids=listify(self.person),
            time=self.time,
            limit=self.limit
        )
        return [ItemQuery(vector, weight * self.weight) for vector, weight in vectors_person_interacted_with]


class RecommendationsItemsQuery(BaseQuery):
    name = "recommendations_to_items"

    class Config(BaseModel):
        person: Union[List[str], str]
        time: str
        limit: int
        weight: float = 1.0

    def __init__(self, db, collection, context, config):
        self.db = db
        self.collection = collection
        self.context = context
        self.person = config.person
        self.weight = config.weight
        self.time = config.time
        self.limit = config.limit

    def get_items(self) -> List[ItemQuery]:
        items = self.db.execute(text("""
        select unnest(search_history.external_item_ids) as id
        from search_history
        where external_person_id = :external_person_id and created > :from_date
        order by created desc
        limit :limit;
        """).params({
            "external_person_id": self.person,
            "limit": self.limit,
            "from_date": time_string_to_datetime_from_now(self.time),
        })).fetchall()
        return [ItemQuery(i.id, self.weight) for i in items]
