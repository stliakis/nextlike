from app.core.searcher.filters.custom.custom import CustomFilter
from app.core.types import SQLQueryCondition, FieldsFilterConfig
from app.models import Collection
from app.utils.base import listify


class FieldsFilter(CustomFilter):
    def __init__(self, db, collection: Collection, fields_column: str = "fields"):
        self.fields_column = fields_column
        self.db = db
        self.collection = collection

    @classmethod
    def is_valid(cls, filter):
        return 'fields' in filter or isinstance(filter, FieldsFilterConfig)

    async def apply(self, filter):
        _params = {}

        builded = self.recursive_build_of_filters(filter.fields, self.fields_column, _params)
        return SQLQueryCondition(sql=" and ".join(builded), params=_params)

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
