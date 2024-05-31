from app.llm.embeddings import OpenAiEmbeddingsCalculator
from app.llm.llm import LLM, GroqLLM, OpenAILLM
from app.resources.cache import get_cache
from app.utils.timeit import Timeit

with Timeit("GroqLLM.single_query"):
    print(GroqLLM().single_query("convert the text to greek if its greeklish: thiki kinitou"))


with Timeit("OpenAILLM.single_query"):
    print(OpenAILLM().single_query("convert the text to greek if its greeklish: thiki kinitou"))
