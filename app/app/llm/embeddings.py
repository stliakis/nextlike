import os
from typing import List

import requests
from more_itertools import batched
from openai import OpenAI

from app.models.search.items.item import Item
from app.resources.cache import Cache
from app.settings import get_settings
from app.utils.base import listify, stable_hash
from app.utils.timeit import Timeit


class EmbeddingsCalculator(object):
    def get_size(self):
        raise NotImplementedError()


class OpenAiEmbeddingsCalculator(EmbeddingsCalculator):
    def __init__(self, model):
        os.environ["OPENAI_API_KEY"] = get_settings().OPENAI_API_KEY
        self.model = model
        self.vectors_size = 1536
        self.client = OpenAI()

    def item_to_string(self, item: Item):
        return item.description

    def fields_to_string(self, fields):
        return ", ".join(
            [
                f"{key}={' '.join(map(str, listify(value)))}"
                for key, value in fields.items()
            ]
        )

    def get_embedding_from_cache(self, string, model):
        with Cache() as cache:
            cache_key = f"embeddings:{model}:{stable_hash(string)}"
            return cache.get(cache_key)

    def set_embedding_to_cache(self, string, model, vector):
        with Cache() as cache:
            cache_key = f"embeddings:{model}:{stable_hash(string)}"
            cache.set(cache_key, vector, 3600 * 24)

    def get_embedding(self, string, model):
        response = self.client.embeddings.create(
            model=model,
            input=string
        )
        return response.data[0].embedding

    def get_embeddings_from_strings(self, strings, model=None):
        if not strings:
            return []

        cached_embeddings = {}
        for string in strings:
            cached_embedding = self.get_embedding_from_cache(string, model)
            if cached_embedding:
                cached_embeddings[string] = cached_embedding

        uncached_strings = [string for string in strings if string not in cached_embeddings]

        if uncached_strings:
            response = self.client.embeddings.create(
                model=model or self.model,
                input=uncached_strings
            )

            calculated_embeddings = {
                uncached_strings[index]: i.embedding for index, i in enumerate(response.data)
            }

            for string, embedding in calculated_embeddings.items():
                self.set_embedding_to_cache(string, model, embedding)

            cached_embeddings.update(calculated_embeddings)

        return [cached_embeddings[string] for string in strings]

    def get_embeddings_from_item(self, item: Item):
        string = self.item_to_string(item)
        vector = list(self.get_embeddings_from_string(string, self.model))
        return vector

    def get_embeddings_from_fields(self, fields: dict):
        string = self.fields_to_string(fields)
        vector = self.get_embeddings_from_string(string)
        return vector

    def get_embeddings_from_string(self, string: str, model=None):
        return self.get_embeddings_from_strings([string], model or self.model)[0]

    def get_embeddings_from_items(self, items: List[Item]):
        strings = [self.item_to_string(item) for item in items]

        all_vectors = []
        for batch in batched(strings, 500):
            all_vectors.extend(self.get_embeddings_from_strings(batch, self.model))

        return all_vectors

    def get_size(self):
        if self.model == "text-embedding-3-large":
            return 3072
        elif self.model == "text-embedding-3-small":
            return 1536
        else:
            return 0


class EmbeddingsProviderCalculator(EmbeddingsCalculator):
    def __init__(self, model, vectors_size=768):
        self.model = model
        self.vectors_size = vectors_size

    def get_size(self):
        return self.vectors_size

    def get_embeddings_from_strings(self, strings):
        with Timeit("embeddings_provider.request"):
            return requests.post(
                get_settings().EMBEDDINGS_PROVIDER_URL + "/embedding",
                json={
                    "model": self.model,
                    "documents": strings
                }
            ).json().get("embeddings")

    def get_embeddings_from_string(self, string):
        return self.get_embeddings_from_strings([string])[0]

    def get_embeddings_from_item(self, item: Item):
        string = item.description
        vector = list(self.get_embeddings_from_string(string))
        return vector

    def get_embeddings_from_items(self, items: List[Item]):
        strings = [item.description for item in items]
        return self.get_embeddings_from_strings(strings)

    def get_embeddings_from_fields(self, fields: dict):
        string = ", ".join(
            [
                f"{key}={' '.join(map(str, listify(value)))}"
                for key, value in fields.items()
            ]
        )
        return self.get_embeddings_from_string(string)

    def get_embedding(self, string):
        return self.get_embeddings_from_string(string)

    def get_embedding_from_cache(self, string, model):
        with Cache() as cache:
            cache_key = f"embeddings:{model}:{stable_hash(string)}"
            return cache.get(cache_key)

    def set_embedding_to_cache(self, string, model, vector):
        with Cache() as cache:
            cache_key = f"embeddings:{model}:{stable_hash(string)}"
            cache.set(cache_key, vector, 3600 * 24)


def get_embeddings_calculator(name):
    if name in ["text-embedding-3-small", "text-embedding-3-large"]:
        type = "openai"
    else:
        type = "st"

    if type == "st":
        if ":" in name:
            model, vectors_size = name.split(":")
            return EmbeddingsProviderCalculator(model, int(vectors_size))
        else:
            return EmbeddingsProviderCalculator(name)
    elif type == "openai":
        return OpenAiEmbeddingsCalculator(name)
    else:
        raise ValueError(f"Unknown Embeddings type: {type}")
