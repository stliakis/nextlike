from app.core.queries.base import BaseQuery
from logging import INFO
from typing import Union, List, Tuple
from pydantic.main import BaseModel

from app.core.types import SimilarityClausePromptPreprocess
from app.llm.llm import get_llm
from app.core.helpers import get_vectors_of_events_for_user, get_query_vector_from_fields, get_query_vector_from_prompt
from app.resources.database import m
from app.settings import get_settings
from app.utils.base import listify, replace_variables_in_string
from app.utils.logging import log


class VectorQuery(BaseModel):
    vector: List[int]
    weight: float = 1.0


class FieldsToVectorQuery(BaseQuery):
    name = "fields_to_vector"

    class Config(BaseModel):
        fields: dict[str, Union[str, int, None, bool, float]]
        weight: float = 1.0

    def __init__(self,
                 db,
                 collection,
                 context, config):
        self.db = db
        self.context = context
        self.collection = collection
        self.fields = config.fields
        self.weight = config.weight
        self.embeddings_calculator = collection.get_embeddings_calculator()

    def get_vectors(self) -> List[VectorQuery]:
        return [VectorQuery(vector=get_query_vector_from_fields(self.db, self.embeddings_calculator, self.fields),
                            weight=self.weight)]


class ItemToVectorQuery(BaseQuery):
    name = "item_to_vector"

    class Config(BaseModel):
        item: Union[List[str], str]
        weight: float = 1.0

    def __init__(self, db, collection, context, config):
        self.db = db
        self.collection = collection
        self.context = context
        self.item = config.item
        self.weight = config.weight

    def get_vectors(self) -> List[VectorQuery]:
        item_ids = listify(self.item)
        items = m.Item.objects(self.db).filter(m.Item.external_id.in_(item_ids)).all()
        return [VectorQuery(vector=item.vector, weight=self.weight) for item in items if item.vector is not None]


class EmbeddingsQuery(BaseQuery):
    name = "embeddings"

    class Config(BaseModel):
        embeddings: List[float]
        weight: float = 1.0

    def __init__(self, db, collection, context, config: Config):
        self.db = db
        self.collection = collection
        self.context = context
        self.embeddings = config.embeddings
        self.weight = config.weight

    def get_vectors(self) -> List[VectorQuery]:
        return [VectorQuery(vector=self.embeddings, weight=self.weight)]


class PromptToVectorQuery(BaseQuery):
    name = "prompt_to_vector"

    class Config(BaseModel):
        prompt: str
        weight: float = 1.0
        preprocess: SimilarityClausePromptPreprocess = None

    def __init__(self, db, collection, context, config):
        self.db = db
        self.collection = collection
        self.embeddings_calculator = collection.get_embeddings_calculator()
        self.context = context
        self.prompt = config.prompt
        self.weight = config.weight
        self.preprocess = config.preprocess

    def preprocess_prompt(self, prompt):

        prompt = replace_variables_in_string(prompt, self.context)

        if self.preprocess:
            llm = get_llm(self.preprocess.model or get_settings().DEFAULT_LLM_PROVIDER_AND_MODEL)

            processed_prompt = llm.single_query(
                f"{self.preprocess.prompt}. The text is the following: '{prompt}'")

            log(INFO, f"processed prompt: {processed_prompt}")

            return processed_prompt
        else:
            return prompt

    def get_vectors(self) -> List[VectorQuery]:
        prompt = self.prompt

        prompt = self.preprocess_prompt(prompt)

        vectors = get_query_vector_from_prompt(self.embeddings_calculator, prompt)

        return [
            VectorQuery(vectors, self.weight)
        ]


class PersonToVectorQuery(BaseQuery):
    name = "person_to_vector"

    class Config(BaseModel):
        person: Union[List[str], str]
        time: str
        limit: int
        weight: float = 1.0

    def __init__(self, db, similarity_engine, context, config: Config):
        self.db = db
        self.similarity_engine = similarity_engine
        self.context = context
        self.person = config.person
        self.time = config.time
        self.limit = config.limit
        self.weight = config.weight

    def get_vectors(self) -> List[VectorQuery]:
        vectors_person_interacted_with = get_vectors_of_events_for_user(
            db=self.db,
            external_person_ids=listify(self.person),
            time=self.time,
            limit=self.limit
        )
        return [VectorQuery(vector=vector, weight=weight * self.weight) for vector, weight in
                vectors_person_interacted_with]
