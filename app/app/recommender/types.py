from datetime import datetime
from typing import Union, List, Optional

import json

from pydantic.fields import Field
from pydantic.main import BaseModel

from app.utils.base import uuid_or_int
import hashlib


class SimpleItem(BaseModel):
    id: Union[str, int]
    fields: dict[str, Union[str, int, float, bool, None, List[Union[str, int, float, bool, None]]]]

    def get_id(self):
        return uuid_or_int(self.id)

    def get_fields_with_hash(self):
        return {
            **self.fields,
            "_hash": self.get_hash()
        }

    def get_hash(self):
        return hashlib.md5(f"${json.dumps(self.fields)}".encode("utf-8")).hexdigest()


class RecommendedItem(BaseModel):
    external_id: Union[str, int]
    id: int
    fields: dict[str, Union[str, int, float, bool, None, List[Union[str, int, float, bool, None]]]]
    score: float


class SimpleEvent(BaseModel):
    event: str = "interaction"
    date: datetime = Field(default_factory=datetime.now)
    person: Union[str, int]
    item: Union[str, int]
    weight: float = 1


class Recommendation(BaseModel):
    items: List[RecommendedItem]
    id: int = None


class CombinedRecommendationConfig(BaseModel):
    pass


class SimilarityClauseFields(BaseModel):
    fields: dict[str, Union[str, int, None, bool, float]]
    weight: float = 1.0


class SimilarityClauseItem(BaseModel):
    item: Union[List[str], str]
    weight: float = 1.0


class SimilarityClausePerson(BaseModel):
    person: Union[List[str], str]
    weight: float = 1.0
    limit: int = 10
    time: str = "all"


class CollaborativeClauseItem(BaseModel):
    item: Union[List[str], str]
    weight: float = 1.0


class CollaborativeClausePerson(BaseModel):
    person: Union[List[str], str]
    weight: float = 1.0
    limit: int = 10
    time: str = "all"


class SimilarityRecommendationConfig(BaseModel):
    of: List[Union[SimilarityClausePerson, SimilarityClauseFields, SimilarityClauseItem]]
    score_threshold: float = 0.01


class CollaborativeRecommendationConfig(BaseModel):
    of: List[Union[CollaborativeClausePerson, CollaborativeClauseItem]]
    minimum_interactions: int = 2


class RecommendationConfig(BaseModel):
    combined: CombinedRecommendationConfig = None
    similar: SimilarityRecommendationConfig = None
    collaborative: CollaborativeRecommendationConfig = None
    filter: dict[str, Union[str, int, float, bool, dict]] = None
    exclude: List[str] = None
    exclude_already_interacted_with_person: str = None
    for_person: Union[str, int] = None
    feedlike: bool = False
    randomize: bool = False
    limit: int = 10
    offset: int = 0
