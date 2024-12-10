from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer, util
from functools import lru_cache
from typing import List

app = FastAPI()


class ModelProvider(object):
    def __init__(self):
        self.models = {}

    def get_model(self, name):
        if name not in self.models:
            print(f"Loading model {name}")
            self.models[name] = SentenceTransformer(name)
            print(f"Model {name} loaded")
        return self.models[name]


class EmbeddingRequest(BaseModel):
    documents: List[str]
    model: str


class SemanticSearchRequest(BaseModel):
    query: str
    documents: List[str]
    model: str


model_provider = ModelProvider()


@lru_cache(maxsize=2048)
def no_batch_embed(sentence: str, model_name: str) -> List[float]:
    model = model_provider.get_model(model_name)
    return model.encode(sentence).tolist()


@app.post("/embedding")
async def embedding(request: EmbeddingRequest):
    embeddings = [no_batch_embed(document, request.model) for document in request.documents]
    return {"embeddings": embeddings}


@app.post("/search")
async def semantic_search(request: SemanticSearchRequest):
    query_embedding = no_batch_embed(request.query)
    document_embeddings = [no_batch_embed(document, request.model) for document in request.documents]
    scores = util.dot_score(query_embedding, document_embeddings).squeeze()
    return {"similarities": [float(s) for s in scores]}
