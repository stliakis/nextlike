import json
import os
from openai import OpenAI
from groq import Groq
from app.resources.cache import Cache
from app.settings import get_settings
from app.utils.base import stable_hash
from app.utils.timeit import Timeit


class LLM(object):
    def __init__(self, model, caching=True):
        self.model = model
        self.caching = caching

    def single_query(self, question):
        raise NotImplementedError


class OpenAILLM(LLM):
    def __init__(self, model=None, **kwargs):
        super().__init__(model or get_settings().DEFAULT_OPENAI_LLM_MODEL, **kwargs)
        os.environ["OPENAI_API_KEY"] = get_settings().OPENAI_API_KEY
        self.client = OpenAI()

    def single_query(self, question):
        with Cache(enabled=self.caching) as cache:
            with Timeit("OpenAILLM.single_query(%s)" % self.model):
                cache_key = f"llm.single_query:{self.model}:{stable_hash(question)}"
                answer = cache.get(cache_key)
                if answer:
                    return answer

                completion = self.client.chat.completions.create(
                    temperature=0,
                    model=self.model or "gpt-4o",
                    messages=[
                        {"role": "system", "content": "Just respond to the question as laconically as possible"},
                        {"role": "user", "content": question}
                    ]
                )

                answer = completion.choices[0].message.content
                cache.set(cache_key, answer, 3600 * 24 * 7)
                return answer

    def function_query(self, question, functions):
        completion = self.client.chat.completions.create(
            temperature=0,
            model=self.model or "gpt-4o",
            tools=functions,
            tool_choice="auto",
            messages=[
                {"role": "system", "content": "Just respond to the question as laconically as possible"},
                {"role": "user", "content": question}
            ]
        )
        print(completion)
        function = completion.choices[0].message.tool_calls[0].function
        return function.name, json.loads(function.arguments)


class GroqLLM(LLM):
    def __init__(self, model, **kwargs):
        super().__init__(model or get_settings().DEFAULT_GROQ_LLM_MODEL, **kwargs)
        self.client = Groq(
            api_key=get_settings().GROQ_API_KEY,
        )

    def single_query(self, question, system_prompts=None):
        with Cache(enabled=self.caching) as cache:
            with Timeit("GroqLLM.single_query(%s)" % self.model):
                cache_key = f"llm.single_query:{self.model}:{stable_hash(question)}"
                answer = cache.get(cache_key)
                if answer:
                    return answer

                messages = [
                    {"role": "user", "content": question}
                ]

                if system_prompts:
                    messages = [{"role": "system", "content": system_prompt} for system_prompt in
                                system_prompts] + messages

                else:
                    messages = [{"role": "system",
                                 "content": "Just respond to the question as laconically as possible"}] + messages

                completion = self.client.chat.completions.create(
                    temperature=0,
                    model=self.model or "llama3-groq-8b-8192-tool-use-preview",
                    messages=messages
                )

                answer = completion.choices[0].message.content
                cache.set(cache_key, answer, 3600 * 24 * 7)
                return answer

    def single_json_query(self, question):
        answer = self.single_query(question, [
            {
                "role": "system",
                "content": "Its important to always respond in plain json, that can be parsed"
            }
        ])

        answer = answer.replace("\\", "").strip()
        return json.loads(answer)

    def function_query(self, question, functions):
        completion = self.client.chat.completions.create(
            temperature=0,
            model=self.model or "llama3-8b-8192",
            tools=functions,
            tool_choice="auto",
            messages=[
                {"role": "system", "content": "Just respond to the question as laconically as possible"},
                {"role": "user", "content": question}
            ]
        )

        function = completion.choices[0].message.tool_calls[0].function
        function_arguments = json.loads(function.arguments)
        if function_arguments.get("properties"):
            function_arguments = function_arguments.get("properties")

        return function.name, {k: v for k, v in function_arguments.items() if v}


def get_llm(name, caching=True):
    if ":" in name:
        type = name.split(":")[0]
        model = name.split(":")[1]
    else:
        type = "openai"
        model = name

    if type == "groq":
        return GroqLLM(model, caching=caching)
    elif type == "openai":
        return OpenAILLM(model, caching=caching)
    else:
        raise ValueError(f"Unknown LLM type: {type}")
