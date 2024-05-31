import os
from openai import OpenAI
from groq import Groq
from app.resources.cache import Cache
from app.settings import get_settings
from app.utils.timeit import Timeit


class LLM(object):
    def __init__(self, model=None):
        self.model = model or get_settings().LLM_MODEL

    def single_query(self, question):
        raise NotImplementedError


class OpenAILLM(LLM):
    def __init__(self, model=None):
        super().__init__(model)
        os.environ["OPENAI_API_KEY"] = get_settings().OPENAI_API_KEY
        self.client = OpenAI()

    def single_query(self, question):
        with Cache() as cache:
            with Timeit("OpenAILLM.single_query(%s)" % self.model):
                cache_key = f"llm.single_query:{self.model}:{hash(question)}"
                answer = cache.get(cache_key)
                if answer:
                    return answer

                completion = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "Just respond to the question as laconically as possible"},
                        {"role": "user", "content": question}
                    ]
                )

                answer = completion.choices[0].message.content
                cache.set(cache_key, answer, 3600 * 24 * 7)
                return answer


class GroqLLM(LLM):
    def __init__(self, model=None):
        super().__init__(model)
        self.client = Groq(
            api_key=get_settings().GROQ_API_KEY,
        )

    def single_query(self, question):
        with Cache() as cache:
            with Timeit("GroqLLM.single_query(%s)" % self.model):
                cache_key = f"llm.single_query:{self.model}:{hash(question)}"
                answer = cache.get(cache_key)
                if answer:
                    return answer

                completion = self.client.chat.completions.create(
                    model="mixtral-8x7b-32768",
                    messages=[
                        {"role": "system", "content": "Just respond to the question as laconically as possible"},
                        {"role": "user", "content": question}
                    ]
                )

                answer = completion.choices[0].message.content
                cache.set(cache_key, answer, 3600 * 24 * 7)
                return answer


def get_llm(name):
    if ":" in name:
        type = name.split(":")[0]
        model = name.split(":")[1]
    else:
        type = "openai"
        model = name

    if type == "groq":
        return GroqLLM(model)
    elif type == "openai":
        return OpenAILLM(model)
    else:
        raise ValueError(f"Unknown LLM type: {type}")
