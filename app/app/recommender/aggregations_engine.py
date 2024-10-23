import copy
import itertools
from sqlalchemy.orm import Session
from app.llm.embeddings import OpenAiEmbeddingsCalculator
from app.llm.llm import get_llm
from app.models import Collection
from app.recommender.recommender import Recommender
from app.recommender.types import (
    RecommendationConfig,
    SimilarityRecommendationConfig,
    SimilarityClauseEmbeddings,
    AggregationConfig,
    AggregationResult,
    CacheConfig, HeavyAndLightLLMStats,
)
from app.settings import get_settings
from app.utils.base import listify, stable_hash
from app.utils.timeit import Timeit


class AggregationsEngine(object):
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

    def query_to_calling_functions(
            self, config: AggregationConfig, possible_aggregation_names=None
    ) -> list:
        functions = []
        for aggregation_config in config.aggregations:
            aggregation_name = aggregation_config.get("name")
            if (
                    possible_aggregation_names
                    and aggregation_name not in possible_aggregation_names
            ):
                continue

            fields = aggregation_config.get("fields", {})

            properties = {}
            required_fields = []
            for field, field_config in fields.items():
                if not isinstance(field_config, dict):
                    continue

                is_multiple = field_config.get("multiple", False)
                field_type = field_config.get("type")

                if field_type in {"text", "item"}:
                    type_str = "string"
                elif field_type == "integer":
                    type_str = "integer"
                else:
                    type_str = "string"

                if not is_multiple:
                    properties[field] = {
                        "type": type_str,
                        "description": field_config.get("description"),
                    }
                else:
                    properties[field] = {
                        "type": "array",
                        "items": {"type": type_str},
                        "description": field_config.get("description"),
                    }

                if field_config.get("enum"):
                    properties[field]["enum"] = field_config.get("enum")

                if field_config.get("required"):
                    required_fields.append(field)

            functions.append(
                {
                    "type": "function",
                    "function": {
                        "name": aggregation_name,
                        "description": aggregation_config.get("description"),
                        "parameters": {
                            "type": "object",
                            "properties": properties,
                            "required": required_fields,
                        },
                    },
                }
            )
        return functions

    def get_llm_question(self, prompt: str) -> str:
        return self.aggregation_prompt.format(prompt=prompt)

    def calculate_embeddings(self, strings: list) -> list:
        with Timeit("AggregationsEngine.calculate_embeddings()"):
            return self.embeddings_calculator.get_embeddings_from_strings(
                strings, model=self.collection.default_embeddings_model
            )

    def find_best_matching_aggregation(self, query: AggregationConfig):
        possible_aggregations = []
        for aggregation_config in query.aggregations:
            aggregation_name = aggregation_config.get("name")
            possible_aggregations.append(
                f"name: {aggregation_name} description: {aggregation_config.get('description')}"
            )

        aggregation_match_query = self.classification_prompt.format(
            categories="\n".join(possible_aggregations), prompt=query.prompt
        )

        print(aggregation_match_query)

        awnser = self.light_llm.single_query(aggregation_match_query)

        print(awnser)

        awnser = awnser.replace("\\", "").strip()

        propable_aggregations = []
        for aggregation_config in query.aggregations:
            aggregation_name = aggregation_config.get("name")
            if aggregation_name in awnser:
                propable_aggregations.append(aggregation_name)

        return propable_aggregations

    def get_structured_query(self, query: AggregationConfig) -> tuple:
        possible_aggregation_names = self.find_best_matching_aggregation(query)

        functions = self.query_to_calling_functions(
            query, possible_aggregation_names=possible_aggregation_names
        )
        question = self.get_llm_question(query.prompt)

        aggregation_name, structured_query = self.heavy_llm.function_query(
            question, functions
        )

        print(
            "aggregation_name", aggregation_name, "structured_query", structured_query
        )

        return aggregation_name, structured_query

    def get_needed_embeddings(
            self, aggregation_config: dict, structured_query: dict
    ) -> dict:
        values_needed_as_embeddings = []
        for field in structured_query:
            field_config = aggregation_config.get("fields", {}).get(field)
            if field_config and field_config.get("type") == "item":
                values_needed_as_embeddings.extend(listify(structured_query.get(field)))

        embeddings_list = self.calculate_embeddings(values_needed_as_embeddings)
        embeddings = dict(zip(values_needed_as_embeddings, embeddings_list))
        return embeddings

    def aggregate(self) -> AggregationResult:
        aggregation_name, structured_query = self.get_structured_query(self.config)

        aggregation = None

        for aggregation in self.config.aggregations:
            if aggregation.get("name") == aggregation_name:
                break

        if not aggregation:
            raise ValueError(
                f"Aggregation '{aggregation_name}' not found in query aggregations."
            )

        embeddings = self.get_needed_embeddings(aggregation, structured_query)

        aggregations_config = aggregation.get("fields", {})
        execution_levels = self.find_execution_levels(aggregations_config)

        suggestions = []
        self.generate_combinations(
            structured_query,
            embeddings,
            aggregations_config,
            execution_levels,
            suggestions,
        )

        self.add_non_dynamic_fields_to_suggestions(aggregation_name, suggestions)

        return AggregationResult(
            aggregation=aggregation_name,
            items=suggestions,
            llm_stats=HeavyAndLightLLMStats(
                heavy_llm_stats=self.heavy_llm.stats, light_llm_stats=self.light_llm.stats
            )
        )

    def add_non_dynamic_fields_to_suggestions(self, aggregation_name, suggestions):
        for aggregation in self.config.aggregations:
            if aggregation.get("name") == aggregation_name:
                for field, field_value in aggregation.get("fields", {}).items():
                    if not isinstance(field_value, dict):
                        for suggestion in suggestions:
                            suggestion[field] = field_value

    def generate_combinations(
            self,
            structured_query: dict,
            embeddings: dict,
            aggregations_config: dict,
            execution_levels: list,
            suggestions: list,
            context: dict = None,
            level_index: int = 0,
    ):
        if context is None:
            context = {}

        if level_index >= len(execution_levels):
            # Reached the end, collect the context
            suggestions.append(context.copy())
            return

        level = execution_levels[level_index]

        # For each field in the current level, get possible values using the current context
        possible_values_per_field = {}

        for field in level:
            field_config = aggregations_config.get(field)

            if not isinstance(field_config, dict):
                continue

            if field_config is None:
                continue

            field_type = field_config.get("type")
            if field_type == "item":
                export_field = field_config.get("item").get("export")
                filters = field_config.get("item").get("filter", {})
                limit = field_config.get("item").get("limit", 1)

                filters = self.replace_filtering_variables(
                    copy.deepcopy(filters), context
                )

                value = context.get(field, structured_query.get(field, None))
                if not value:
                    continue

                if isinstance(value, list):
                    possible_values = []
                    for value in value:
                        embedding = embeddings.get(value)

                        if not embedding:
                            continue

                        recommender = Recommender(
                            db=self.db,
                            collection=self.collection,
                            config=RecommendationConfig(
                                cache=CacheConfig(expire=3600, key=stable_hash(f"{filters}_{value}_{limit}")),
                                filter=filters,
                                similar=SimilarityRecommendationConfig(
                                    of=[
                                        SimilarityClauseEmbeddings(embeddings=embedding)
                                    ]
                                ),
                                limit=limit,
                            ),
                        )

                        recs = recommender.get_recommendation()

                        for item in recs.items:
                            possible_values.append(item.fields[export_field])

                    possible_values_per_field[field] = possible_values
                else:
                    embedding = embeddings.get(value)
                    if not embedding:
                        continue

                    recommender = Recommender(
                        db=self.db,
                        collection=self.collection,
                        config=RecommendationConfig(
                            cache=CacheConfig(expire=3600, key=stable_hash(f"{filters}_{value}_{limit}")),
                            filter=filters,
                            similar=SimilarityRecommendationConfig(
                                of=[SimilarityClauseEmbeddings(embeddings=embedding)]
                            ),
                            limit=limit,
                        ),
                    )

                    recs = recommender.get_recommendation()

                    # Extract possible values for the field
                    possible_values = [rec.fields[export_field] for rec in recs.items]

                    if not possible_values:
                        return

                    possible_values_per_field[field] = possible_values
            elif field_type in ["integer", "text"]:
                # Use the value from the structured query or context
                value = context.get(field, structured_query.get(field, ""))

                possible_values = [value]

                possible_values_per_field[field] = possible_values

        # Generate all combinations of possible values for fields in this level
        fields_in_level = list(possible_values_per_field.keys())
        values_in_level = list(possible_values_per_field.values())

        for combination in itertools.product(*values_in_level):
            new_context = context.copy()
            print(f"Combination: {combination}")
            for field, value in zip(fields_in_level, combination):
                if value:
                    new_context[field] = value
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
