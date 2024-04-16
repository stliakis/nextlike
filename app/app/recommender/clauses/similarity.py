from typing import Union, List, Tuple

from app.recommender.helpers import get_vectors_of_events_for_user
from app.resources.database import m
from app.utils.base import listify


class SimilarityClause(object):
    def get_vectors(self) -> List[Tuple[List[int], float]]:
        raise NotImplementedError


class FieldsToVectorClause(SimilarityClause):
    def __init__(self, similarity_engine, fields: dict[str, Union[str, int, None, bool, float]], weight: float = 1.0):
        self.similarity_engine = similarity_engine
        self.db = self.similarity_engine.db
        self.fields = fields
        self.weight = weight

    @classmethod
    def from_of(cls, similarity_engine, of):
        if hasattr(of, 'fields'):
            return cls(similarity_engine, of.fields, of.weight)

    def get_vectors(self) -> List[Tuple[List[int], float]]:
        return [(self.similarity_engine.get_query_vector(self.fields), self.weight)]


class ItemToVectorClause(SimilarityClause):
    def __init__(self, similarity_engine, item: Union[List[str], str], weight: float = 1.0):
        self.similarity_engine = similarity_engine
        self.db = self.similarity_engine.db
        self.item = item
        self.weight = weight

    @classmethod
    def from_of(cls, similarity_engine, of):
        if hasattr(of, 'item'):
            return cls(similarity_engine, of.item, of.weight)

    def get_vectors(self) -> List[Tuple[List[int], float]]:
        item_ids = listify(self.item)
        items = m.Item.objects(self.db).filter(m.Item.external_id.in_(item_ids)).all()
        vectors_similar_to_item_id = [(item.vectors_1536, self.weight) for item in items]
        return vectors_similar_to_item_id


class PersonToVectorClause(SimilarityClause):
    def __init__(self, similarity_engine, person: Union[List[str], str], weight: float = 1.0):
        self.similarity_engine = similarity_engine
        self.db = self.similarity_engine.db
        self.person = person
        self.weight = weight

    @classmethod
    def from_of(cls, similarity_engine, of):
        if hasattr(of, 'person'):
            return cls(similarity_engine, of.person, of.weight)

    def get_vectors(self) -> List[Tuple[List[int], float]]:
        vectors_person_interacted_with = get_vectors_of_events_for_user(
            self.similarity_engine.db,
            listify(self.person)
        )
        return [(vector, weight * self.weight) for vector, weight in vectors_person_interacted_with]
