from datetime import datetime
from typing import Union, List, Dict, Any

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


class SearchItem(BaseModel):
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


class SearchResult(BaseModel):
    items: List[SearchItem]
    id: int = None


class CombinedSearchConfig(BaseModel):
    pass


class SearchPersonClause(BaseModel):
    person_recommendations: str
    weight: float = 1.0
    limit: int = 500
    time: str = "7d"


class SortingModifier(BaseModel):
    score_name: str = None
    topn: int = 1000
    weight: float = 0.5


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


class QueryClausePrompt(BaseModel):
    query: str
    weight: float = 1.0
    distance_function: str = None
    preprocess: SimilarityClausePromptPreprocess = None


class SimilarityClauseEmbeddings(BaseModel):
    embeddings: List[float]
    weight: float = 1.0


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


class CacheConfig(BaseModel):
    expire: int = 3600
    key: str = None


class LLMStats(BaseModel):
    total_tokens: int = 0


class HeavyAndLightLLMStats(BaseModel):
    heavy_llm_stats: LLMStats = None
    light_llm_stats: LLMStats = None


class AggregationResult(BaseModel):
    aggregation: str
    items: list
    llm_stats: HeavyAndLightLLMStats = None


class SimilaritySearchConfig(BaseModel):
    of: List[Union[
        SimilarityClausePerson, SimilarityClauseFields, SimilarityClauseItem, SimilarityClausePrompt, SimilarityClauseEmbeddings, QueryClausePrompt]]
    score_threshold: float = None
    distance_function: str = "cosine"
    sort: SortingModifier = None


class CollaborativeSearchConfig(BaseModel):
    of: List[Union[CollaborativeClausePerson, CollaborativeClauseItem, SearchPersonClause]]
    minimum_interactions: int = 2


class SearchConfig(BaseModel):
    combined: CombinedSearchConfig = None
    similar: SimilaritySearchConfig = None
    collaborative: CollaborativeSearchConfig = None
    filter: Dict = None
    exclude: List[Union[CollaborativeClausePerson, CollaborativeClauseItem, SearchPersonClause]] = []
    exclude_already_interacted_with_person: str = None
    for_person: Union[str, int] = None
    randomize: bool = False
    limit: int = 10
    offset: int = 0
    cache: CacheConfig = None


class AggregationsSortingModifier(BaseModel):
    field: str
    order: str = "asc"


class AggregationFieldItemConfig(BaseModel):
    filter: Dict[str, Union[str, Dict[str, str]]] = None
    export: str
    limit: int = 1
    sort: SortingModifier = None
    distance_function: str = None


class AggregationFieldConfig(BaseModel):
    type: str = "text"
    value: Union[str, int, float, dict, list] = None
    description: str
    multiple: bool = False
    item: AggregationFieldItemConfig = None
    enum: Union[List[str], Dict[str, str]] = None


class AggregationQueryConfig(BaseModel):
    name: str
    description: str = None
    facts: List[str] = []
    fields: Dict[str, AggregationFieldConfig]


class AggregationConfig(BaseModel):
    aggregations: List[AggregationQueryConfig]
    limit: int = 1
    sort: AggregationsSortingModifier = None
    prompt: str
    files: List[dict] = []
    light_llm: str = None
    heavy_llm: str = None
    classification_prompt: str = None
    aggregation_prompt: str = None
    caching: bool = True
