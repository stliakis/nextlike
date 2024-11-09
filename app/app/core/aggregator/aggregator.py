import asyncio
import copy
import itertools
from app.utils.logging import log
from typing import List, Dict

from sqlalchemy.orm import Session
from app.llm.embeddings import OpenAiEmbeddingsCalculator
from app.llm.llm import get_llm
from app.models import Collection
from app.core.searcher.searcher import Searcher
from app.core.types import (
    SearchConfig,
    SimilaritySearchConfig,
    AggregationConfig,
    AggregationResult,
    HeavyAndLightLLMStats, QueryClausePrompt, SortingModifier, CacheConfig, AggregationFieldConfig,
)
from app.settings import get_settings
from app.utils.base import listify, stable_hash
from app.utils.timeit import Timeit


class Aggregator(object):
    def __init__(self, db: Session, collection: Collection, config: AggregationConfig):
        self.db = db
        self.collection = collection
        self.light_llm = get_llm(
            config.light_llm or get_settings().AGGREGATIONS_LIGHT_LLM, caching=config.caching
        )
        self.heavy_llm = get_llm(
            config.heavy_llm or get_settings().AGGREGATIONS_HEAVY_LLM, caching=config.caching
        )
        self.embeddings_calculator = OpenAiEmbeddingsCalculator()
        self.config = config

        self.classification_prompt = (
                config.classification_prompt
                or """
Assign to Categories: Match the query to one or more of the most relevant categories from the list below, selecting up to three categories that best fit.

Categories:
{categories}

Instructions:
Identify the category names that best match the user's query and write just them. Don't say anything else.

User's Query:
{prompt}
        """
        )

        self.aggregation_prompt = (
                config.aggregation_prompt
                or """
Call the correct function for the following query:
{prompt}
        """
        )

    def replace_filtering_variables(self, filters: dict, context: dict) -> dict:
        for key, value in filters.items():
            if isinstance(value, dict):
                filters[key] = self.replace_filtering_variables(value, context)
            elif isinstance(value, str) and value.startswith("$"):
                filters[key] = context.get(value[1:])
        return filters

    def config_ddl_to_openapi(self, config_ddl: Dict[str, AggregationFieldConfig]):
        """
        Transforms a custom config DDL dictionary into a valid OpenAPI properties definition.

        Args:
            config_ddl (dict): The configuration DDL dictionary to transform.

        Returns:
            dict: A dictionary representing the OpenAPI properties definition.
        """

        type_mapping = {
            'string': ('string', None),
            'text': ('string', None),
            'integer': ('integer', None),
            'float': ('number', 'float'),
            'double': ('number', 'double'),
            'boolean': ('boolean', None)
        }

        def recurse(node):
            if isinstance(node, dict):
                if 'type' in node:
                    node_type = node['type']
                    if node_type == 'list':
                        # Handle list type
                        items_schema = recurse(node.get('of', {}))
                        result = {
                            'type': 'array',
                            'items': items_schema
                        }
                        if 'description' in node:
                            result['description'] = node['description']
                        return result
                    elif node_type == 'object':
                        # Handle object type
                        properties = {}
                        required = []
                        for key, value in node.get('properties', {}).items():
                            properties[key] = recurse(value)
                            if isinstance(value, dict) and value.get('required', False):
                                required.append(key)
                        result = {
                            'type': 'object',
                        }

                        if properties:
                            result['properties'] = properties

                        if required:
                            result['required'] = required
                        if 'description' in node:
                            result['description'] = node['description']
                        return result
                    elif node_type == 'item':
                        # Handle 'item' type
                        schema = recurse(node.get('item', {}))
                        if 'description' in node:
                            schema['description'] = node['description']
                        if 'multiple' in node and node['multiple']:
                            schema = {
                                'type': 'array',
                                'items': schema
                            }

                        if 'enum' in node:
                            if isinstance(node['enum'], dict):
                                # Handle enum dictionary case
                                enum_values = list(node['enum'].keys())
                                enum_descriptions = [f"{k}: {v}" for k, v in node['enum'].items()]
                                schema['enum'] = enum_values
                                # Append enum descriptions to the field description
                                existing_description = schema.get('description', '')
                                schema['description'] = (f"{existing_description} Possible values: " +
                                                         ", ".join(enum_descriptions)).strip()
                            else:
                                schema['enum'] = node['enum']

                        return schema
                    else:
                        # Handle primitive types and enums
                        openapi_type, openapi_format = type_mapping.get(node_type, ('string', None))
                        schema = {'type': openapi_type}
                        if openapi_format:
                            schema['format'] = openapi_format
                        if 'description' in node:
                            schema['description'] = node['description']
                        if 'enum' in node:
                            if isinstance(node['enum'], dict):
                                # Handle enum dictionary case
                                enum_values = list(node['enum'].keys())
                                enum_descriptions = [f"{k} is {v}" for k, v in node['enum'].items()]
                                schema['enum'] = enum_values
                                # Append enum descriptions to the field description
                                existing_description = schema.get('description', '')
                                schema['description'] = (f"{existing_description} Possible values: " +
                                                         ", ".join(enum_descriptions)).strip()
                            else:
                                schema['enum'] = node['enum']

                        if 'multiple' in node and node['multiple']:
                            schema = {
                                'type': 'array',
                                'items': schema
                            }
                        return schema
                elif 'object' in node or 'objects' in node:
                    # Handle nested object without explicit type
                    properties = {}
                    required = []
                    obj_key = 'object' if 'object' in node else 'objects'
                    for key, value in node[obj_key].items():
                        properties[key] = recurse(value)
                        if isinstance(value, dict) and value.get('required', False):
                            required.append(key)
                    result = {
                        'type': 'object',
                        'properties': properties
                    }
                    if required:
                        result['required'] = required
                    if 'description' in node:
                        result['description'] = node['description']
                    return result
                else:
                    # Handle simple field with description or default case
                    schema = {}
                    if 'description' in node:
                        schema['description'] = node['description']
                    if 'enum' in node:
                        schema['enum'] = node['enum']

                    if 'type' in node:
                        openapi_type, openapi_format = type_mapping.get(node['type'], ('string', None))
                        schema['type'] = openapi_type
                        if openapi_format:
                            schema['format'] = openapi_format
                    else:
                        schema['type'] = 'string'
                    if 'multiple' in node and node['multiple']:
                        schema = {
                            'type': 'array',
                            'items': schema
                        }
                    return schema
            elif isinstance(node, str):
                # Handle string descriptions
                return {
                    'type': 'string',
                    'description': node
                }
            else:
                # Default case
                return {'type': 'string'}

        # Start recursion and collect required fields at the top level
        schema = {
            'type': 'object',
            'properties': {},
            'required': []
        }
        for key, value in config_ddl.items():
            schema['properties'][key] = recurse(value)
            if isinstance(value, dict) and value.get('required', False):
                schema['required'].append(key)
        if not schema['required']:
            schema.pop('required')
        return schema

    def query_to_calling_functions(
            self, config: AggregationConfig, possible_aggregation_names=None
    ) -> list:
        functions = []
        for possible_aggregation in possible_aggregation_names:
            for aggregation_config in config.aggregations:
                aggregation_name = aggregation_config.name

                if possible_aggregation != aggregation_name:
                    continue

                fields = aggregation_config.fields

                function_description = aggregation_config.description

                if aggregation_config.facts:
                    function_description = """
                    {function_description}
                    Facts:
                    {facts}
                    """.format(
                        function_description=function_description,
                        facts="\n".join(aggregation_config.facts)
                    )

                functions.append(
                    {
                        "type": "function",
                        "function": {
                            "name": aggregation_name,
                            "description": function_description,
                            "parameters": self.config_ddl_to_openapi(fields),
                        },
                    }
                )

        log("debug", functions)

        return functions

    def get_llm_question(self, prompt: str) -> str:
        return self.aggregation_prompt.format(prompt=prompt)

    def calculate_embeddings(self, strings: list) -> list:
        with Timeit("Aggregator.calculate_embeddings()"):
            return self.embeddings_calculator.get_embeddings_from_strings(
                strings, model=self.collection.default_embeddings_model
            )

    def find_best_matching_aggregation(self, query: AggregationConfig):
        possible_aggregations = []

        if len(query.aggregations) == 1:
            return query.aggregations[0].name

        for aggregation_config in query.aggregations:
            aggregation_name = aggregation_config.name
            possible_aggregations.append(
                f"name: {aggregation_name} description: {aggregation_config.description}"
            )

        aggregation_match_query = self.classification_prompt.format(
            categories="\n".join(possible_aggregations), prompt=query.prompt
        )

        print(aggregation_match_query)

        awnser = self.light_llm.single_query(aggregation_match_query)

        awnser = awnser.replace("\\", "").replace(",", " ").replace("\n", " ").strip()

        log("info", "light query result: %s" % awnser)

        propable_aggregations = []

        for word in awnser.split(" "):
            for aggregation_config in query.aggregations:
                aggregation_name = aggregation_config.name
                if aggregation_name == word.strip():
                    propable_aggregations.append(aggregation_name)

        print("aggregations:", propable_aggregations)

        return propable_aggregations

    async def get_structured_queries(self, config: AggregationConfig) -> list[tuple]:
        possible_aggregation_names = self.find_best_matching_aggregation(config)

        functions = self.query_to_calling_functions(
            config, possible_aggregation_names=possible_aggregation_names
        )

        functions = functions[:config.limit]

        question = self.get_llm_question(config.prompt)

        if config.limit <= 1:
            tasks = [self.heavy_llm.function_query(question, functions, config.files)]
        else:
            tasks = [
                self.heavy_llm.function_query(question, [function]) for function in functions
            ]

        results = await asyncio.gather(*tasks)

        return [
            (aggregation_name, structured_query) for aggregation_name, structured_query in results
        ]

    def get_needed_embeddings(
            self, structured_queries
    ) -> dict:
        values_needed_as_embeddings = []

        for aggregation_name, structured_query in structured_queries:
            aggregation_config = None
            for aggregation in self.config.aggregations:
                if aggregation.name == aggregation_name:
                    aggregation_config = aggregation
                    break

            for field in structured_query:
                field_config = aggregation_config.fields.get(field)
                if field_config.type == "item":
                    values_needed_as_embeddings.extend(listify(structured_query.get(field)))

        embeddings_list = self.calculate_embeddings(values_needed_as_embeddings)
        embeddings = dict(zip(values_needed_as_embeddings, embeddings_list))
        return embeddings

    def sort_structured_queries(self, structured_queries):
        if self.config.sort:
            def get_field_value(value):
                if not value:
                    return 0

                if isinstance(value, str) and str(value).isdigit():
                    return int(value)

                return value

            structured_queries = sorted(
                structured_queries,
                key=lambda x: get_field_value(x[1].get(self.config.sort.field)),
                reverse=self.config.sort.order == "desc",
            )

        return structured_queries

    async def aggregate(self) -> List[AggregationResult]:
        structured_queries = await self.get_structured_queries(self.config)

        log("info", "Structured queries:", structured_queries)

        structured_queries = self.sort_structured_queries(structured_queries)

        aggregation_results = []

        # embeddings = self.get_needed_embeddings(structured_queries)

        for aggregation_name, structured_query in structured_queries:
            aggregation = None

            for aggregation in self.config.aggregations:
                if aggregation.name == aggregation_name:
                    break

            if not aggregation:
                raise ValueError(
                    f"Aggregation '{aggregation_name}' not found in query aggregations."
                )

            aggregations_config = aggregation.fields

            # log("debug", aggregations_config)
            execution_levels = self.find_execution_levels(aggregations_config)

            suggestions = []
            self.generate_combinations(
                structured_query,
                None,
                aggregations_config,
                execution_levels,
                suggestions,
            )

            self.add_non_dynamic_fields_to_suggestions(aggregation_name, suggestions)

            print("sguss:",suggestions)

            aggregation_results.append(
                AggregationResult(
                    aggregation=aggregation_name,
                    items=suggestions,
                    llm_stats=HeavyAndLightLLMStats(
                        heavy_llm_stats=self.heavy_llm.stats, light_llm_stats=self.light_llm.stats
                    )
                )
            )

        return aggregation_results

    def add_non_dynamic_fields_to_suggestions(self, aggregation_name, suggestions):
        for aggregation in self.config.aggregations:
            if aggregation.name == aggregation_name:
                for field, field_value in aggregation.fields.items():
                    if field_value.value:
                        for suggestion in suggestions:
                            suggestion[field] = field_value.value

    def generate_combinations(
            self,
            structured_query: dict,
            embeddings: dict,
            aggregations_config: Dict[str, AggregationFieldConfig],
            execution_levels: list,
            suggestions: list,
            context: dict = None,
            level_index: int = 0,
    ):
        if context is None:
            context = {}

        if level_index >= len(execution_levels):
            print("adding:",context.copy())

            suggestions.append(context.copy())
            return

        level = execution_levels[level_index]

        possible_values_per_field = {}

        for field in level:
            field_config = aggregations_config.get(field)

            if field_config is None:
                continue

            field_type = field_config.type
            if field_type == "item":
                export_field = field_config.item.export
                filters = field_config.item.filter
                limit = field_config.item.limit

                filters = self.replace_filtering_variables(
                    copy.deepcopy(filters), context
                )

                value = context.get(field, structured_query.get(field, None))
                if not value:
                    continue

                value = listify(value)

                possible_values = []

                sort_modifier = field_config.item.sort

                for value in value:
                    # embedding = embeddings.get(value)
                    #
                    # if not embedding:
                    #     continue
                    recommender = Searcher(
                        db=self.db,
                        collection=self.collection,
                        config=SearchConfig(
                            cache=CacheConfig(expire=3600, key=stable_hash(f"{filters}_{value}_{limit}")),
                            filter=filters,
                            similar=SimilaritySearchConfig(
                                of=[
                                    QueryClausePrompt(
                                        query=value,
                                        distance_function=field_config.item.distance_function
                                    )
                                ],
                                sort=sort_modifier
                            ),
                            limit=limit,
                        ),
                    )

                    search = recommender.search()

                    print(search.items)

                    for item in search.items:
                        possible_values.append(item.fields[export_field])

                possible_values_per_field[field] = possible_values

            elif field_type in ["integer", "text", "list"]:
                # Use the value from the structured query or context
                value = context.get(field, structured_query.get(field, ""))

                possible_values = [value]

                possible_values_per_field[field] = possible_values

        # Generate all combinations of possible values for fields in this level
        fields_in_level = list(possible_values_per_field.keys())
        values_in_level = list(possible_values_per_field.values())

        for combination in itertools.product(*values_in_level):

            print("combination:",combination)
            new_context = context.copy()
            for field, value in zip(fields_in_level, combination):
                if value:
                    new_context[field] = value

            print("new conten:",new_context)
            # Recursively generate combinations for the next levels
            self.generate_combinations(
                structured_query,
                embeddings,
                aggregations_config,
                execution_levels,
                suggestions,
                context=new_context,
                level_index=level_index + 1,
            )

    def find_execution_levels(self, aggregations: dict) -> list:
        def extract_dependencies(obj, deps):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and value.startswith("$"):
                        dep_field = value[1:]
                        deps.add(dep_field)
                    else:
                        extract_dependencies(value, deps)
            elif isinstance(obj, list):
                for item in obj:
                    extract_dependencies(item, deps)

        dependencies = {}
        dependents = {}
        nodes = set(aggregations.keys())
        in_degree = {}

        for field_name in aggregations:
            dependencies[field_name] = set()
            dependents[field_name] = set()
            in_degree[field_name] = 0

        for field_name, field_config in aggregations.items():
            if not isinstance(field_config, dict):
                continue

            deps = set()
            if "filter" in field_config.get("item", {}):
                extract_dependencies(field_config.get("item").get("filter"), deps)
            actual_deps = deps & nodes
            dependencies[field_name] = actual_deps
            in_degree[field_name] = len(actual_deps)
            for dep in actual_deps:
                dependents[dep].add(field_name)

        levels = []
        processed = set()

        while len(processed) < len(nodes):
            current_level = [
                node for node in nodes if in_degree[node] == 0 and node not in processed
            ]
            if not current_level:
                raise Exception("Circular dependency detected")
            levels.append(current_level)
            for node in current_level:
                processed.add(node)
                for dependent in dependents.get(node, []):
                    if dependent in in_degree:
                        in_degree[dependent] -= 1
        return levels
