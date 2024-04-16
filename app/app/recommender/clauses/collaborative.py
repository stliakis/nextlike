from typing import Union, List, Tuple

from app.recommender.helpers import get_vectors_of_events_for_user, get_external_item_ids_of_events_for_user
from app.utils.base import listify


class CollaborativeClause(object):
    def get_items(self) -> List[Tuple[str, float]]:
        raise NotImplementedError


class ItemToItemsClause(CollaborativeClause):
    def __init__(self, collaborative_engine, item: Union[List[str], str], weight: float = 1.0):
        self.collaborative_engine = collaborative_engine
        self.item = item
        self.weight = weight

    @classmethod
    def from_of(cls, collaborative_engine, of):
        if hasattr(of, 'item'):
            return cls(collaborative_engine, of.item, of.weight)

    def get_items(self) -> List[Tuple[str, float]]:
        items = listify(self.item)
        return [(item, self.weight) for item in items]


class PersonItemsClause(CollaborativeClause):
    def __init__(self, collaborative_engine, person: Union[List[str], str], weight: float = 1.0):
        self.collaborative_engine = collaborative_engine
        self.person = person
        self.weight = weight

    @classmethod
    def from_of(cls, collaborative_engine, of):
        if hasattr(of, 'person'):
            return cls(collaborative_engine, of.person, of.weight)

    def get_items(self) -> List[Tuple[str, float]]:
        vectors_person_interacted_with = get_external_item_ids_of_events_for_user(
            self.collaborative_engine.db,
            listify(self.person)
        )
        return [(vector, weight * self.weight) for vector, weight in vectors_person_interacted_with]
