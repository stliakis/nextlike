from app.core.searcher.filters.custom.fields import FieldsFilter
from app.core.searcher.filters.custom.natural_language import NaturalLanguageQueryFilter
from app.models import Collection
from sqlalchemy.orm import Session


class FilteredEngine(object):
    fields_column = "fields"
    db: Session
    collection: Collection

    async def build_query_string_and_params(self, filters):
        filter_processors = [
            NaturalLanguageQueryFilter,
            FieldsFilter,
        ]

        sql_queries = []

        for filter in filters:
            for filter_processor in filter_processors:
                if filter_processor.is_valid(filter):
                    processor = filter_processor(db=self.db, collection=self.collection)
                    sql_query = await processor.apply(filter)
                    sql_queries.append(sql_query)
                    break

        all_conditions = [sql.sql for sql in sql_queries if sql.sql]
        all_params = {}
        for sql in sql_queries:
            all_params.update(sql.params)

        return " and ".join(all_conditions), all_params
