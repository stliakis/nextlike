from logging import INFO, log
from typing import List, Tuple

from app.core.types import AggregationConfig, NaturalQueryToSQL
from app.llm.llm import get_llm
from app.settings import get_settings
from app.utils.base import replace_variables_in_string


class NaturalQueryClause(object):
    def get_queries(self) -> List[Tuple[List[int], float]]:
        raise NotImplementedError


class NaturalQuerySearchClause(NaturalQueryClause):
    def __init__(self, db, similarity_engine, query: str, weight: float = 1.0, distance_function: str = None,
                 preprocess=None):
        self.db = db
        self.similarity_engine = similarity_engine
        self.query = query
        self.weight = weight
        self.preprocess = preprocess
        self.distance_function = distance_function

    @classmethod
    def from_of(cls, db, similarity_engine, of, context):
        if hasattr(of, 'query'):
            return cls(db, similarity_engine, replace_variables_in_string(of.query, context), weight=of.weight,
                       preprocess=of.preprocess,
                       distance_function=of.distance_function)

    def preprocess_query(self, query):
        if self.preprocess:
            llm = get_llm(self.preprocess.model or get_settings().DEFAULT_LLM_PROVIDER_AND_MODEL)

            processed_query = llm.single_query(f"{self.preprocess.prompt}. The text is the following: '{query}'")

            log(INFO, f"processed prompt: {processed_query}")

            return processed_query
        else:
            return query

    async def get_sql_queries(self) -> List[NaturalQueryToSQL]:
        query = self.query

        query = self.preprocess_query(query)
        from app.core.aggregator.aggregator import Aggregator
        aggregator = await Aggregator(self.db, self.similarity_engine.collection, AggregationConfig(
            prompt=query,
            aggregations=[
                {
                    "name": "search",
                    "description": "convert a natural language query to an sql query, its argument contains variables for the sql query",
                    "fields": {
                        "field_category": {
                            "multiple": True,
                            "description": "the category of the item",
                        },
                        "field_make": {
                            "multiple": True,
                            "description": "the manufacturer of the item",
                            "type": "text",
                        },
                        "field_model": {
                            "multiple": True,
                            "description": "the model of the item",
                            "type": "text",
                        },
                        "field_area": {
                            "multiple": True,
                            "description": "the area in square meters"
                        },
                        "field_price": {
                            "multiple": True,
                            "description": "the price of the item",
                            "type": "float",
                        },
                        "field_floor": {
                            "multiple": True,
                            "description": "the floor of the building",
                        },
                        "field_rooms": {
                            "multiple": True,
                            "type": "integer",
                            "description": "the number of rooms",
                        },
                        "field_engine_size": {
                            "multiple": True,
                            "description": "the displacement of the engine",
                            "type": "integer",
                        },
                        "final_sql": {
                            "description": "the final sql query but with the arguments as ':argument_name_{index of value in the passed argument list}' etc with, important to never include variable values inside the sql script, all variables should be with :argument_name. Include only the part after where, dont finish with semicolon",
                            "type": "text"
                        },
                        "search_title_english": {
                            "description": "the auto generated title for the search",
                        },
                        "search_title_greek": {
                            "description": "the auto generated title for the search",
                        }
                    }
                }

            ],
            limit=3,
            heavy_llm="openai:gpt-4o",
            aggregation_prompt="""
            you are an expert system that converts natural language queries to sql queries that query the fields json column of 
            the table 'item'. Use postgres jsonb function to access the fields, each argument of the function is a field that
            can be accessed as item.fields->>'field_name'. Convert the following natural language query, the argument params type should always be correct
             always convert the full query when possible include and or and complex sql:

            {prompt}""",

        )).aggregate()

        print(aggregator)

        ag = aggregator[0].items[0]

        params = {}

        sql = ag["final_sql"]

        for field, values in ag.items():
            if not field.startswith("field_"):
                continue
            for index, value in enumerate(values):
                params["%s_%s" % (field, index)] = value

            sql = sql.replace("'%s'" % field, "'%s'" % field.replace("field_", ""))

        return [
            NaturalQueryToSQL(sql=sql, params=params)
        ]
