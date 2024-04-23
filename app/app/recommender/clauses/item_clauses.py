from typing import Union, List, Tuple

from sqlalchemy import text

from app.recommender.helpers import get_vectors_of_events_for_user, get_external_item_ids_of_events_for_user
from app.utils.base import listify, time_string_to_datetime_from_now


class CollaborativeClause(object):
    def get_items(self) -> List[Tuple[str, float]]:
        raise NotImplementedError


class ItemToItemsClause(CollaborativeClause):
    def __init__(self, db, item: Union[List[str], str], weight: float = 1.0):
        self.db = db
        self.item = item
        self.weight = weight

    @classmethod
    def from_of(cls, db, of):
        if hasattr(of, 'item'):
            return cls(db, of.item, of.weight)

    def get_items(self) -> List[Tuple[str, float]]:
        items = listify(self.item)
        return [(item, self.weight) for item in items]


class PersonItemsClause(CollaborativeClause):
    def __init__(self, db, person: Union[List[str], str], time: str, limit: int, weight: float = 1.0):
        self.db = db
        self.person = person
        self.weight = weight
        self.time = time
        self.limit = limit

    @classmethod
    def from_of(cls, db, of):
        if hasattr(of, 'person'):
            return cls(db, of.person, of.time, of.limit, of.weight)

    def get_items(self) -> List[Tuple[str, float]]:
        vectors_person_interacted_with = get_external_item_ids_of_events_for_user(
            db=self.db,
            external_person_ids=listify(self.person),
            time=self.time,
            limit=self.limit
        )
        return [(vector, weight * self.weight) for vector, weight in vectors_person_interacted_with]


class RecommendationsItemsClause(CollaborativeClause):
    def __init__(self, db, person_recommendations: Union[List[str], str], time: str, limit: int, weight: float = 1.0):
        self.db = db
        self.person_recommendations = person_recommendations
        self.weight = weight
        self.time = time
        self.limit = limit

    @classmethod
    def from_of(cls, db, of):
        if hasattr(of, 'person_recommendations'):
            return cls(db, of.person_recommendations, of.time, of.limit, of.weight)

    def get_items(self) -> List[Tuple[str, float]]:
        items = self.db.execute(text("""
        select unnest(search_history.external_item_ids) as id
        from search_history
        where external_person_id = :external_person_id and created > :from_date
        order by created desc
        limit :limit;
        """).params({
            "external_person_id": self.person_recommendations,
            "limit": self.limit,
            "from_date": time_string_to_datetime_from_now(self.time),
        })).fetchall()
        return [(i.id, self.weight) for i in items]
