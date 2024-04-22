from typing import Union, List, Tuple

from app.recommender.helpers import get_vectors_of_events_for_user, get_external_item_ids_of_events_for_user
from app.utils.base import listify


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
