import base64
import json
import os
from io import BytesIO
from pprint import pprint

from openai import OpenAI, AsyncOpenAI
from groq import Groq, AsyncGroq

from app.recommender.types import LLMStats
from app.resources.cache import Cache
from app.settings import get_settings
from app.utils.base import stable_hash
from app.utils.timeit import Timeit
from pdf2image import convert_from_bytes


class LLM(object):
    def __init__(self, model, caching=True):
        self.model = model
        self.caching = caching
        self.stats = LLMStats()

    def single_query(self, question):
        raise NotImplementedError

    def files_to_llm_files(self, files):
        messages = []

        file_contents = [
            {
                "type": "text",
                "text": "Extract the data from the files",
            },
        ]
        for file in files:
            if file.get("type") == "image":
                if file.get("base64"):
                    file_contents.append({
                        "type": "image_url",
                        "image_url": {
                            "detail": "low",
                            "url": f"data:image/jpeg;base64,{file.get('base64')}",
                        },
                    })
            elif file.get("type") == "pdf":
                if file.get("base64"):
                    # Decode base64 to get the PDF as bytes
                    pdf_bytes = base64.b64decode(file.get("base64"))

                    # Convert PDF bytes to images
                    images = convert_from_bytes(pdf_bytes)

                    # Convert each image to base64
                    base64_images = []
                    for i, image in enumerate(images):
                        buffered = BytesIO()
                        image.save(buffered, format="PNG")  # You can also use 'JPEG' if preferred
                        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                        base64_images.append(img_base64)

                        image_data = base64.b64decode(img_base64)

                        # Write the decoded data to a file
                        with open(str(i) + ".png", "wb") as file:
                            file.write(image_data)

                    # print("bas:", base64_images)



                    for image in base64_images:
                        file_contents.append({
                            "type": "image_url",
                            "image_url": {
                                "detail": "high",
                                "url": f"data:image/png;base64,{image}",
                            },
                        })

                    print("coun:", len(file_contents))

        messages.append({
            "role": "user",
            "content": file_contents
        })

        return messages


class OpenAILLM(LLM):
    client = None

    def __init__(self, model=None, **kwargs):
        super().__init__(model or get_settings().DEFAULT_OPENAI_LLM_MODEL, **kwargs)
        os.environ["OPENAI_API_KEY"] = get_settings().OPENAI_API_KEY

        with Timeit("initializing client"):
            if not OpenAILLM.client:
                OpenAILLM.client = OpenAI()
                OpenAILLM.async_client = AsyncOpenAI()

            self.async_client = OpenAILLM.async_client
            self.client = OpenAILLM.client

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

                self.stats.total_tokens += completion.usage.total_tokens

                cache.set(cache_key, answer, 3600 * 24 * 7)
                return answer

    async def function_query(self, question, functions, files=None):
        with Cache(enabled=self.caching) as cache:
            with Timeit("OpenAILLM.function_query(%s)" % self.model):
                cache_key = f"OpenAILLM.function_query:{self.model}:{stable_hash(question)}:{stable_hash(str(functions))}"
                cached = cache.get(cache_key)
                if cached:
                    return cached[0], cached[1]

                messages = [
                    {"role": "system", "content": "Just respond to the question as laconically as possible"},
                ]

                if files:
                    messages.extend(self.files_to_llm_files(files))

                messages.append({"role": "user", "content": question})

                completion = await self.async_client.chat.completions.create(
                    temperature=0,
                    model=self.model or "gpt-4o",
                    tools=functions,
                    tool_choice="required",
                    messages=messages
                )

                function = completion.choices[0].message.tool_calls[0].function

                self.stats.total_tokens += completion.usage.total_tokens

                function_name = function.name
                arguments = json.loads(function.arguments)

                cache.set(cache_key, [function_name, arguments], 3600 * 24 * 7)

                return function_name, arguments


class GroqLLM(LLM):
    def __init__(self, model, **kwargs):
        super().__init__(model or get_settings().DEFAULT_GROQ_LLM_MODEL, **kwargs)
        self.client = Groq(
            api_key=get_settings().GROQ_API_KEY,
        )
        self.async_client = AsyncGroq(
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

                self.stats.total_tokens += completion.usage.total_tokens

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

    async def function_query(self, question, functions):
        with Cache(enabled=self.caching) as cache:
            with Timeit("GroqLLM.function_query(%s)" % self.model):
                cache_key = f"GroqLLM.function_query:{self.model}:{stable_hash(question)}:{stable_hash(str(functions))}"
                cached = cache.get(cache_key)
                if cached:
                    return cached[0], cached[1]

                completion = await self.async_client.chat.completions.create(
                    temperature=0,
                    model=self.model or "llama3-8b-8192",
                    tools=functions,
                    tool_choice="auto",
                    messages=[
                        {"role": "system", "content": "Just respond to the question as laconically as possible"},
                        {"role": "user", "content": question}
                    ]
                )

                print(completion)

                function = completion.choices[0].message.tool_calls[0].function
                function_arguments = json.loads(function.arguments)

                self.stats.total_tokens += completion.usage.total_tokens

                if function_arguments.get("properties"):
                    function_arguments = function_arguments.get("properties")

                function_name = function.name
                arguments = {k: v for k, v in function_arguments.items() if v}

                cache.set(cache_key, [function_name, arguments], 3600 * 24 * 7)

                return function_name, arguments


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
