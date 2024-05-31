import os
from openai import OpenAI

from app.resources.cache import Cache
from app.settings import get_settings
from app.utils.timeit import Timeit


class LLM(object):
    def __init__(self, model=None):
        os.environ["OPENAI_API_KEY"] = get_settings().OPENAI_API_KEY
        self.client = OpenAI()
        self.model = model or get_settings().LLM_MODEL

    def single_query(self, question):
        with Timeit("LLM.single_query"):
            with Cache() as cache:
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
                cache.set(cache_key, answer, 3600 * 24)
                return answer
