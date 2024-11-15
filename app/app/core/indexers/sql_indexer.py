from typing import List, Dict
from sqlalchemy import text
import numpy as np
from redis.commands.search.query import Query
from redis.commands.search.field import TagField, VectorField, TextField, NumericField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType

from app.core.indexers.indexer import Indexer
from app.core.indexers.types import IndexerResultItem
from app.easytests.interact import interact
from app.resources.database import m
from app.resources.rdb import get_redis
from app.utils.base import chunks, clear, listify
from app.utils.logging import log


class SQLIndexer(Indexer):
    def __init__(self, db, collection, index_embeddings=True):
        super(SQLIndexer, self).__init__(db, collection)
        self.client = get_redis()

    def get_vectors_size(self):
        if self.collection.default_embeddings_model == "text-embedding-3-large":
            return 3072
        elif self.collection.default_embeddings_model == "text-embedding-3-small":
            return 1536
        else:
            return 0

    async def recreate(self):
        pass

    async def cleanup(self):
        pass

    @classmethod
    async def cleanup_all(cls, db):
        pass

    async def build_sql_filters(self, filters):
        _params = {}
        builded = self.recursive_build_of_filters(filters, "fields", _params)
        return " and ".join(builded), _params

    async def search(
            self,
            filters=None,
            text_search_query=None,
            text_search_similarity_function=None,
            vector=None,
            limit=10,
            offset=0,
            exclude_external_ids=None,
            raw_query=None,
            score_threshold=0
    ):
        all_where_clauses: List[str] = []
        all_where_params: Dict[str, any] = {}

        if filters:
            filters_query, filter_params = await self.build_sql_filters(filters)
            if filters_query:
                all_where_clauses.append(filters_query)
            all_where_params.update(filter_params)

        if exclude_external_ids:
            all_where_clauses.append("not item.external_id = any(:exclude_ids)")
            all_where_params.update({
                "exclude_ids": exclude_external_ids
            })

        all_where_clauses.append("item.collection_id = :collection_id")
        all_where_params.update({
            "collection_id": self.collection.id
        })

        query_params = {
            "limit": limit,
            "offset": offset,
            "score_threshold": score_threshold
        }

        if score_threshold:
            score_threshold_query = "similarity_table.similarity > :score_threshold"
            query_params["score_threshold"] = score_threshold
        else:
            score_threshold_query = None

        query_params.update(all_where_params)

        distance_query = None
        distance_function = "cosine"

        if vector and distance_function in ["cosine", "inner_product", "l1", "l2"]:
            query_params.update({
                "vector": "[%s]" % (",".join(map(str, vector)))
            })

            if len(vector) == 1536:
                vector_field = "vectors_1536"
                all_where_clauses.append("item.vectors_1536 is not null")
            elif len(vector) == 3072:
                vector_field = "vectors_3072"
                all_where_clauses.append("item.vectors_3072 is not null")
            else:
                raise ValueError("Query vector must be of length 1536 or 3072")

            if distance_function == "cosine":
                distance_query = f"1 - (item.{vector_field} <=> :vector) as similarity"
            elif distance_function == "inner_product":
                distance_query = f"(item.{vector_field} <#> :vector) * -1 as similarity"
            elif distance_function == "l1":
                distance_query = f"(item.{vector_field} <+> :vector) as similarity"
            elif distance_function == "l2":
                distance_query = f"1 - (item.{vector_field} <-> :vector) as similarity"
        elif text_search_query:
            distance_query = "({all_query}) as similarity".format(
                all_query=f"similarity(description, :query)"
            )
            query_params.update({
                "query": text_search_query
            })
        else:
            distance_query = "1 as similarity"

        order_by = "similarity_table.similarity desc"

        pagination_query = "limit :limit offset :offset"

        query = text("""
           select id,description,similarity from (
               select item.id,item.external_id,item.description,item.fields,item.scores, {distance_query} from item {where_clauses}
               ) as similarity_table {score_threshold_query} order by {order_by} {pagination_query}
        """.format(
            where_clauses=f"where {' and '.join(all_where_clauses)}" if all_where_clauses else "",
            order_by=order_by,
            topn=limit,
            distance_query=distance_query or "",
            pagination_query=pagination_query,
            score_threshold_query=f"where {score_threshold_query}" if score_threshold_query else "",
        )).params(query_params)

        log("info", "similarity items query: %s, %s" % (query, query_params))

        items = self.db.execute(query)

        # print("tite:", [i for i in items])

        return [IndexerResultItem(
            id=item.id,
            description=item.description,
            similarity=item.similarity
        ) for item in items]

    def transform_value(self, value, double_quote=False):
        if isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, list):
            return [self.transform_value(v, double_quote=double_quote) for v in value]

        if double_quote:
            return f'"{value}"'
        else:
            return str(value)

    def build_condition(self, key, value, fields_column, params, negate=False):
        conditions = []
        param_index = len(params)

        if isinstance(value, dict):
            for op, op_value in value.items():
                if op in ["not"]:
                    # Handle "not" operator with recursion
                    nested_conditions = self.build_condition(key, op_value, fields_column, params, not negate)
                    conditions.extend([f"NOT ({c})" for c in nested_conditions])
                else:
                    param_key = f"{key}_{op}_{param_index}"
                    if op in ["gte", "lte", "eq"]:
                        field_casted = f"CAST({fields_column}->>'{key}' AS double precision)"
                        operator = ">=" if op == "gte" else ("<=" if op == "lte" else "=")
                        condition = f"{field_casted} {operator} :{param_key}"
                        if negate:
                            condition = f"NOT ({condition})"
                        conditions.append(condition)
                        params[param_key] = self.transform_value(op_value)
                    elif op == "contains":
                        op_value = listify(op_value)
                        condition = f"{fields_column}->'{key}' @> (:{param_key})::jsonb"
                        if negate:
                            condition = f"NOT ({condition})"
                        conditions.append(condition)
                        params[param_key] = f"[{','.join(self.transform_value(op_value, double_quote=True))}]"
                    elif op == "in":
                        op_value = listify(op_value)
                        condition = f"({fields_column}->'{key}')::text = any(:{param_key})"
                        if negate:
                            condition = f"NOT ({condition})"
                        conditions.append(condition)
                        params[param_key] = self.transform_value(op_value, double_quote=True)
                    elif op == "overlaps":
                        op_value = listify(op_value)
                        condition = f"ARRAY(SELECT jsonb_array_elements_text({fields_column}->'{key}')) && :{param_key}"
                        if negate:
                            condition = f"NOT ({condition})"
                        conditions.append(condition)
                        params[param_key] = self.transform_value(op_value, double_quote=False)

        else:
            # Direct equality, with casting to double precision for numerical values
            param_key = f"{key}_eq_{param_index}"
            condition = f"{fields_column}->>'{key}' = :{param_key}"
            if negate:
                condition = f"NOT ({condition})"
            conditions.append(condition)
            params[param_key] = self.transform_value(value)

        return conditions

    def recursive_build_of_filters(self, filters, fields_column, params, level=0):
        conditions = []
        logical_operator = ' AND ' if level == 0 else ' OR '

        for key, value in filters.items():
            if key in ['and', 'or', 'not']:
                nested_conditions = [self.recursive_build_of_filters(subfilter, fields_column, params, level + 1) for
                                     subfilter
                                     in
                                     value] if key in ['and', 'or'] else [
                    self.recursive_build_of_filters(value, fields_column, params, level + 1)]
                grouped_conditions = f"({' AND '.join(nested_conditions)})" if key == 'and' else f"({' OR '.join(nested_conditions)})"
                if key == 'not':
                    grouped_conditions = f"NOT ({grouped_conditions})"
                conditions.append(grouped_conditions)
            else:
                conditions += self.build_condition(key, value, fields_column, params)

        sql = ' AND '.join(conditions) if level == 0 else f"({logical_operator.join(conditions)})"

        if sql:
            return [sql]

        return []
