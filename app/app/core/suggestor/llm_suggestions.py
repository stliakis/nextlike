from typing import List

from app.core.suggestor.context_providers import ContextProvider
from app.llm.llm import get_llm


class LLMSuggestions(object):
    def __init__(self, db, collection, contexts: List[ContextProvider], extra_info, model):
        self.collection = collection
        self.llm = get_llm(model)
        self.db = db
        self.extra_info = extra_info
        self.contexts = contexts
        self.system_prompt = """
        You are an expert suggestion system. Write {limit} Autocomplete suggestions for the query based on the context, each suggestion should start with the user query.Finish any half-written query.
        One suggestion on each line, dont write the numbers of items! try to guest the next query!.
        """

        self.prompt_template = """
Context:
{context}

Query:
{query}

{info}
        """

    def construct_prompt(self, query):
        contexts = []

        for context in self.contexts:
            contexts.append(context.get_context())

        context_string = "\n\n".join(contexts)

        return self.prompt_template.format(context=context_string, query=query, info=self.extra_info)

    def get_suggestions(self, query, limit=10):
        prompt = self.construct_prompt(query)
        suggestions = self.llm.single_query(prompt, system_prompts=[self.system_prompt.format(limit=limit)])
        suggestions = suggestions.replace("\n\n", "\n").split("\n")

        suggestions = [suggestion.strip() for suggestion in suggestions][:limit]

        print(suggestions)

        suggestions = [suggestion for suggestion in suggestions if suggestion]

        return suggestions

    def get_items(self, query):
        suggestions = self.get_suggestions(query)

        return suggestions
