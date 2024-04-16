from app.utils.base import listify


def build_condition(key, value, fields_column, params, negate=False):
    conditions = []
    param_index = len(params)

    if isinstance(value, dict):
        for op, op_value in value.items():
            if op in ["not"]:
                # Handle "not" operator with recursion
                nested_conditions = build_condition(key, op_value, fields_column, params, not negate)
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
                    params[param_key] = op_value
                elif op == "contains":
                    op_value = listify(op_value)
                    condition = f"{fields_column}->'{key}' @> (:{param_key})::jsonb"
                    if negate:
                        condition = f"NOT ({condition})"
                    conditions.append(condition)
                    params[param_key] = f"['{','.join(map(str, op_value))}']".replace("'", '"')
                elif op == "in":
                    in_conditions = []
                    for v in op_value:
                        in_param_key = f"{param_key}_in_{len(in_conditions)}"
                        in_condition = f"{fields_column}->>'{key}' = :{in_param_key}"
                        if negate:
                            in_condition = f"NOT ({in_condition})"
                        in_conditions.append(in_condition)
                        params[in_param_key] = v
                    conditions.append(f"({' OR '.join(in_conditions)})")
    else:
        # Direct equality, with casting to double precision for numerical values
        param_key = f"{key}_eq_{param_index}"
        condition = f"{fields_column}->>'{key}' = :{param_key}"
        if negate:
            condition = f"NOT ({condition})"
        conditions.append(condition)
        params[param_key] = value

    return conditions


def recursive_build(filters, fields_column, params, level=0):
    conditions = []
    logical_operator = ' AND ' if level == 0 else ' OR '

    for key, value in filters.items():
        if key in ['and', 'or', 'not']:
            nested_conditions = [recursive_build(subfilter, fields_column, params, level + 1) for subfilter in
                                 value] if key in ['and', 'or'] else [
                recursive_build(value, fields_column, params, level + 1)]
            grouped_conditions = f"({' AND '.join(nested_conditions)})" if key == 'and' else f"({' OR '.join(nested_conditions)})"
            if key == 'not':
                grouped_conditions = f"NOT ({grouped_conditions})"
            conditions.append(grouped_conditions)
        else:
            conditions += build_condition(key, value, fields_column, params)

    return ' AND '.join(conditions) if level == 0 else f"({logical_operator.join(conditions)})"


def build_query_string_and_params(fields_column, filters):
    params = {}
    conditions = recursive_build(filters, fields_column, params)
    return conditions, params
