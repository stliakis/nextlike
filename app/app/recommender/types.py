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
    person_id: Union[str, int]
    item_id: Union[str, int]
    weight: float = 1


class Recommendation(BaseModel):
    items: List[RecommendedItem]
    id: int = None


class CombinedRecommendationConfig(BaseModel):
    pass


class SimilarityRecommendationConfig(BaseModel):
    similar_to_fields: dict[str, Union[str, int, None, bool, float]] = None
    similar_to_item_id: Union[List[Union[str, int]], Union[str, int]] = None
    person_id: Union[str, int] = None
    exclude_ids: List[Union[str, int]] = None
    exclude_already_interacted_with_person_id: str = None
    similarity_threshold: float = 0.01


class CollaborativeRecommendationConfig(BaseModel):
    item_id: Union[List[Union[str, int]], None] = None
    person_id: Union[List[Union[str, int]], None] = None
    minimum_interactions: int = 2
    exclude_already_interacted_with_person_id: str = None
    exclude_ids: List[Union[str, int]] = None


class RecommendationConfig(BaseModel):
    combined: Optional[CombinedRecommendationConfig] = None
    similarity: Optional[SimilarityRecommendationConfig] = None
    collaborative: Optional[CollaborativeRecommendationConfig] = None
    filters: dict[str, Union[str, int, float, bool, dict]] = None
    for_person_id: Union[str, int] = None
    feedlike: bool = False
    randomize: bool = False
    limit: int = 10
    offset: int = 0
