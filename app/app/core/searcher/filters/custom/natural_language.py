from logging import INFO

from app.core.types import SQLQueryCondition, AggregationConfig, NaturalLanguageQueryFilterConfig
from app.llm.llm import get_llm
from app.models import Collection, ItemsField
from app.settings import get_settings
from app.utils.logging import log


class NaturalLanguageQueryFilter(object):
    def __init__(self,
                 db,
                 collection: Collection):
        self.db = db
        self.collection = collection
        self.preprocess = None

    @classmethod
    def is_valid(cls, filter):
        return 'query' in filter or isinstance(filter, NaturalLanguageQueryFilterConfig)

    async def apply(self, filter):
        return {}
        # return await self.get_sql_queries(filter.query)

    def preprocess_query(self, query):
        if self.preprocess:
            llm = get_llm(self.preprocess.model or get_settings().DEFAULT_LLM_PROVIDER_AND_MODEL)

            processed_query = llm.single_query(f"{self.preprocess.prompt}. The text is the following: '{query}'")

            log(INFO, f"processed prompt: {processed_query}")

            return processed_query
        else:
            return query
    #
    # async def get_fields(self):
    #     fields = []
    #
    #     for field in ItemsField.objects(self.db).filter(
    #             ItemsField.collection_id == self.collection.id
    #     ):
    #         ## select distinct values of field  item.fields->'field_name' from item
    #         # query = f"-- select distinct item.fields->'{field.field_name}' as value from item"
    #         # values = [i.value for i in self.db.execute(text(query)).fetchall()]
    #         #
    #         # print("vales:", values)
    #
    #         fields.append("name={name} type={type} label={label}".format(
    #             name=field.field_name,
    #             type=field.type,
    #             label=field.field_label
    #         ))
    #
    #     return fields

#     async def get_sql_queries(self, query) -> SQLQueryCondition:
#         query = self.preprocess_query(query)
#
#         print("getting:", query)
#
#         from app.core.aggregator.aggregator import Aggregator
#
#         aggregation_fields = {
#             "final_sql": {
#                 "description": """
# the final sql query but with the arguments as :argument_<index>
# etc with, important to never include variable values inside the sql script and always include the variable names as seen in the arguments
# , all variables should be with :argument_<index>.
# Include only the part after where, dont finish with semicolon""",
#                 "type": "text"
#             },
#             "arguments_list": {
#                 "required": True,
#                 "multiple": True,
#                 "type": "text",
#                 "description": "the arguments for the final sql query",
#             },
#             "search_title_english": {
#                 "required": True,
#                 "description": "the auto generated title for the search",
#             },
#             "search_title_greek": {
#                 "required": True,
#                 "description": "the auto generated title for the search",
#             }
#         }
#
#         aggregator = await Aggregator(self.db, self.collection, AggregationConfig(
#             prompt=query,
#             aggregations=[
#                 {
#                     "name": "search",
#                     "description": "convert a natural language query to an sql query, its argument contains variables for the sql query",
#                     "fields": aggregation_fields
#                 }
#
#             ],
#             limit=3,
#             heavy_llm="openai:gpt-4o-mini",
#             aggregation_prompt="""
#             you are an expert system that converts natural language queries to sql queries that query the fields json column of
#             the table 'item'. Use postgres jsonb function to access the fields, each argument of the function is a field that
#             can be accessed as item.fields->>'field_name'. Convert the following natural language query, the argument params type should always be correct
#              always convert the full query when possible include and or and complex sql:
#
#             available_fields:
#             %s
#
#             {prompt}""" % (
#                 "\n".join(await self.get_fields()),
#             ),
#
#         )).aggregate()
#
#         ag = aggregator[0].items[0]
#
#         params = {}
#
#         sql = ag["final_sql"]
#         sql_params = ag["arguments_list"]
#
#         for index, var in enumerate(sql_params):
#             params[f"argument_{index}"] = var
#
#         print("params:", params)
#         print("sql:", sql)
#
#         return SQLQueryCondition(sql=sql, params=params)
