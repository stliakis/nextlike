import os
from typing import Union, List
from more_itertools import batched
from openai.embeddings_utils import get_embedding, get_embeddings

from app.models.recommendations.items.item import Item
from app.settings import get_settings
from app.utils.base import listify


class EmbeddingsCalculator(object):
    vectors_size = None


class OpenAiEmbeddingsCalculator(EmbeddingsCalculator):
    def __init__(self, model=None):
        os.environ["OPENAI_API_KEY"] = get_settings().OPENAI_API_KEY
        self.model = model or get_settings().OPENAI_EMBEDDINGS_MODEL
        self.vectors_size = 1536

    def item_to_string(self, item: Item):
        return item.description

    def fields_to_string(self, fields):
        return ", ".join(
            [
                f"{key}={' '.join(map(str, listify(value)))}"
                for key, value in fields.items()
            ]
        )

    def get_embeddings_from_item(self, item: Item):
        string = self.item_to_string(item)
        vector = list(get_embedding(string, self.model))
        return vector

    def get_embeddings_from_fields(self, fields: dict):
        string = self.fields_to_string(fields)
        vector = list(get_embedding(string, self.model))
        return vector

    def get_embeddings_from_string(self, string: str):
        vector = list(get_embedding(string, self.model))
        return vector

    def get_embeddings_from_items(self, items: List[Item]):
        strings = [self.item_to_string(item) for item in items]

        all_vectors = []
        for batch in batched(strings, 64):
            all_vectors.extend(get_embeddings(batch, self.model))

        return all_vectors

    def get_embeddings_from_fields(
            self, fields: dict[str, Union[str, int, float, bool]]
    ):
        string = self.fields_to_string(fields)
        vector = get_embedding(string, self.model)
        return vector
