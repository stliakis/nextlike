from typing import Union, List, Tuple

from app.recommender.helpers import get_vectors_of_events_for_user
from app.resources.database import m
from app.utils.base import listify


class SimilarityClause(object):
    def get_vectors(self) -> List[Tuple[List[int], float]]:
        raise NotImplementedError


class FieldsToVectorClause(SimilarityClause):
    def __init__(self, db, fields: dict[str, Union[str, int, None, bool, float]], weight: float = 1.0):
        self.db = db
        self.fields = fields
        self.weight = weight

    @classmethod
    def from_of(cls, db, of):
        if hasattr(of, 'fields'):
            return cls(db, of.fields, of.weight)

    def get_vectors(self) -> List[Tuple[List[int], float]]:
        return [(self.db.get_query_vector_from_fields(self.fields), self.weight)]


class ItemToVectorClause(SimilarityClause):
    def __init__(self, db, item: Union[List[str], str], weight: float = 1.0):
        self.db = db
        self.item = item
        self.weight = weight

    @classmethod
    def from_of(cls, db, of):
        if hasattr(of, 'item'):
            return cls(db, of.item, of.weight)

    def get_vectors(self) -> List[Tuple[List[int], float]]:
        item_ids = listify(self.item)
        items = m.Item.objects(self.db).filter(m.Item.external_id.in_(item_ids)).all()
        vectors_similar_to_item_id = [(item.vector, self.weight) for item in items]
        return vectors_similar_to_item_id


class PromptToVectorClause(SimilarityClause):
    def __init__(self, db, prompt: str, weight: float = 1.0):
        self.db = db
        self.prompt = prompt
        self.weight = weight

    @classmethod
    def from_of(cls, db, of):
        if hasattr(of, 'prompt'):
            return cls(db, of.prompt)

    def get_vectors(self) -> List[Tuple[List[int], float]]:
        prompt = self.prompt
        vectors = self.db.get_query_vector_from_prompt(prompt)
        return [
            (vectors, self.weight)
        ]


class PersonToVectorClause(SimilarityClause):
    def __init__(self, db, person: Union[List[str], str], time: str, limit: int, weight: float = 1.0):
        self.db = db
        self.person = person
        self.time = time
        self.limit = limit
        self.weight = weight

    @classmethod
    def from_of(cls, db, of):
        if hasattr(of, 'person'):
            return cls(db, of.person, of.time, of.limit, of.weight)

    def get_vectors(self) -> List[Tuple[List[int], float]]:
        vectors_person_interacted_with = get_vectors_of_events_for_user(
            db=self.db,
            external_person_ids=listify(self.person),
            time=self.time,
            limit=self.limit
        )
        return [(vector, weight * self.weight) for vector, weight in vectors_person_interacted_with]
