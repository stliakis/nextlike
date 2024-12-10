from datetime import datetime
from typing import Union, List, Dict, Any, Literal

import json

from pydantic.fields import Field
from pydantic.main import BaseModel
from app.utils.base import uuid_or_int
import hashlib


class ItemDescriptionPreprocess(BaseModel):
    model: str = None
    prompt: str


class SimpleItem(BaseModel):
    id: str
    fields: Dict = {}
    scores: Dict[str, float] = {}
    description: str = None
    description_from_fields: List[str] = None
    description_preprocess: ItemDescriptionPreprocess = None

    def get_id(self):
        return uuid_or_int(self.id)

    def get_fields_with_hash(self):
        return {**self.fields, "_hash": self.get_hash()}

    def get_hash(self):
        return hashlib.md5(f"${json.dumps(self.fields)}".encode("utf-8")).hexdigest()


class SimplePerson(BaseModel):
    id: Union[str, int]
    fields: Dict = {}


class SearchItem(BaseModel):
    id: Union[str, int]
    fields: Dict
    score: float = None
    scores: Dict[str, float] = {}
    exported: Union[Any, Dict[str, Any]] = None
    description: str = None


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
    similar_to_fields: dict[str, Union[str, int, None, bool, float]]
    weight: float = 1.0


class SimilarityClauseItem(BaseModel):
    item: Union[List[str], str]
    weight: float = 1.0


class FieldsClause(BaseModel):
    fields: dict[str, Union[str, int, None, bool, float]]
    weight: float = 1.0


class SimilarityClausePromptPreprocess(BaseModel):
    model: str = None
    prompt: str


class SimilarityClausePrompt(BaseModel):
    prompt: str
    weight: float = 1.0
    preprocess: SimilarityClausePromptPreprocess = None


class TextClausePrompt(BaseModel):
    text: str
    weight: float = 1.0
    distance_function: str = None
    preprocess: SimilarityClausePromptPreprocess = None
    score_threshold: float = None


class NaturalQueryClause(BaseModel):
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


class SuggestionResult(BaseModel):
    items: list


class SimilaritySearchConfig(BaseModel):
    of: List[
        Union[
            SimilarityClausePerson,
            SimilarityClauseFields,
            SimilarityClauseItem,
            SimilarityClausePrompt,
            SimilarityClauseEmbeddings,
            TextClausePrompt,
            NaturalQueryClause,
            FieldsClause
        ]
    ]
    type: Literal["text_then_vector", "vector_then_text"] = "text_then_vector"


class CollaborativeSearchConfig(BaseModel):
    of: List[
        Union[CollaborativeClausePerson, CollaborativeClauseItem, SearchPersonClause]
    ]
    minimum_interactions: int = 2


class FilterQueryConfig(BaseModel):
    pass


class NaturalLanguageQueryFilterConfig(FilterQueryConfig):
    query: str
    model: str = None


class FieldsFilterConfig(FilterQueryConfig):
    fields: Dict[str, Union[str, int, float, bool, dict]]


class SearchRankConfig(BaseModel):
    score_function: str = None
    topn: int = None
    randomize: bool = False


class SearchConfig(BaseModel):
    similar: SimilaritySearchConfig = None
    collaborative: CollaborativeSearchConfig = None
    filters: List[Union[FilterQueryConfig]] = []
    filter: Dict = {}
    exclude: List[
        Union[CollaborativeClausePerson, CollaborativeClauseItem, SearchPersonClause]
    ] = []
    exclude_already_interacted_with_person: str = None
    for_person: Union[str, int] = None
    randomize: bool = False
    limit: int = 10
    offset: int = 0
    export: Union[str, List[str]] = None
    rank: SearchRankConfig = None
    cache: Union[CacheConfig, None] = CacheConfig(expire=3600, key=None)


class FilterConfig(BaseModel):
    custom: List[FilterQueryConfig] = []


class AggregationsSortingModifier(BaseModel):
    field: str
    order: str = "asc"


class AggregationFieldSearchConfig(SearchConfig):
    similar: SimilaritySearchConfig = SimilaritySearchConfig(of=[])
    cache: Union[CacheConfig, None] = CacheConfig(expire=3600, key=None)


class AggregationFieldConfig(BaseModel):
    type: str = "text"
    value: Union[str, int, float, dict, list] = None
    description: str
    multiple: bool = False
    search: AggregationFieldSearchConfig = None
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
    heavy_model: str = None
    light_model: str = None
    classification_prompt: str = None
    aggregation_prompt: str = None
    # cache: Union[CacheConfig, bool] = CacheConfig(
    #     expire=3600,
    #     key=None
    # )

    cache: Union[CacheConfig, None] = None


class SuggestAggregationConfig(AggregationConfig):
    collection: str


class SuggestSearchConfig(SearchConfig):
    collection: str


class AutoCompleteContextConfig(BaseModel):
    type: str
    context_title: str
    search: SearchConfig


class AutoCompleteConfig(BaseModel):
    query: str
    extra_info: str = None
    contexts: List[AutoCompleteContextConfig]
    model: str


class SuggestConfig(BaseModel):
    autocomplete: AutoCompleteConfig = None
    search: SuggestSearchConfig = None
    aggregate: SuggestAggregationConfig = None
    limit: int = 1


class SQLQueryCondition(BaseModel):
    sql: str
    params: dict


class TextClauseQuery(BaseModel):
    query: str
    weight: float = 1.0
    distance_function: str = None
    score_threshold: float = None


class Suggestion(BaseModel):
    type: str
    id: str = None
    aggregation_name: str = None
    item_id: str = None
    fields: dict = None
    score: float = None

    def is_same(self, suggestion):
        return json.dumps(self.fields, sort_keys=True) == json.dumps(
            suggestion.fields, sort_keys=True
        )


class AutocompleteResult(BaseModel):
    items: List[SearchItem]
