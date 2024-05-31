from datetime import datetime
from typing import Union, List, Dict

import json

from pydantic.fields import Field
from pydantic.main import BaseModel

from app.utils.base import uuid_or_int
import hashlib


class SimpleItem(BaseModel):
    id: Union[str, int]
    fields: Dict = {}
    scores: Dict[str, float] = {}
    description: str = None
    description_from_fields: List[str] = None

    def get_id(self):
        return uuid_or_int(self.id)

    def get_fields_with_hash(self):
        return {
            **self.fields,
            "_hash": self.get_hash()
        }

    def get_hash(self):
        return hashlib.md5(f"${json.dumps(self.fields)}".encode("utf-8")).hexdigest()


class SimplePerson(BaseModel):
    id: Union[str, int]
    fields: Dict = {}


class RecommendedItem(BaseModel):
    id: Union[str, int]
    fields: Dict
    similarity: float = None
    score: float = None


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


class SimilarityClausePromptPreprocess(BaseModel):
    model: str = None
    prompt: str


class SimilarityClausePrompt(BaseModel):
    prompt: str
    weight: float = 1.0
    preprocess: SimilarityClausePromptPreprocess = None


class SimilarityClausePerson(BaseModel):
    person: Union[List[str], str]
    weight: float = 1.0
    limit: int = 10
    time: str = "1M"


class CollaborativeClauseItem(BaseModel):
    item: Union[List[str], str]
    weight: float = 1.0


class CollaborativeClausePerson(BaseModel):
    person: Union[List[str], str]
    weight: float = 1.0
    limit: int = 10
    time: str = "1M"


class RecommendationsPersonClause(BaseModel):
    person_recommendations: str
    weight: float = 1.0
    limit: int = 500
    time: str = "7d"


class SortingModifier(BaseModel):
    score_name: str = None
    topn: int = 1000
    weight: float = 0.5


class SimilarityRecommendationConfig(BaseModel):
    of: List[Union[SimilarityClausePerson, SimilarityClauseFields, SimilarityClauseItem, SimilarityClausePrompt]]
    score_threshold: float = None
    distance_function: str = "cosine"
    sort: SortingModifier = None


class CollaborativeRecommendationConfig(BaseModel):
    of: List[Union[CollaborativeClausePerson, CollaborativeClauseItem, RecommendationsPersonClause]]
    minimum_interactions: int = 2


class CacheConfig(BaseModel):
    expire: int = 3600


class RecommendationConfig(BaseModel):
    combined: CombinedRecommendationConfig = None
    similar: SimilarityRecommendationConfig = None
    collaborative: CollaborativeRecommendationConfig = None
    filter: Dict = None
    exclude: List[Union[CollaborativeClausePerson, CollaborativeClauseItem, RecommendationsPersonClause]] = []
    exclude_already_interacted_with_person: str = None
    for_person: Union[str, int] = None
    randomize: bool = False
    limit: int = 10
    offset: int = 0
    cache: CacheConfig = None
