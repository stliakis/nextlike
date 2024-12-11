from datetime import datetime
from typing import Union, List, Dict, Any

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


class SimpleEvent(BaseModel):
    event: str = "interaction"
    date: datetime = Field(default_factory=datetime.now)
    person: Union[str, int]
    item: Union[str, int]
    weight: float = 1



class SimilarityClausePromptPreprocess(BaseModel):
    model: str = None
    prompt: str


class CacheConfig(BaseModel):
    expire: int = 3600
    key: str = None


class LLMStats(BaseModel):
    total_tokens: int = 0


class HeavyAndLightLLMStats(BaseModel):
    heavy_llm_stats: LLMStats = None
    light_llm_stats: LLMStats = None
