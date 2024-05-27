from app.llm.embeddings import OpenAiEmbeddingsCalculator
from app.llm.llm import LLM
from app.resources.cache import get_cache

print(LLM().single_query("convert the text to greek if its greeklish: thiki kinitou"))
# print(OpenAiEmbeddingsCalculator().get_embeddings(["hello", "hello2"], "text-embedding-3-small"))
