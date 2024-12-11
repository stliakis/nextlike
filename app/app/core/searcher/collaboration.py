# from sqlalchemy import text
# from typing import List, Union, Tuple
#
# from app.models.collection import Collection
# from app.models.search.items.item import Item
# from app.core.helpers import get_external_item_ids_of_events_for_user
# from app.core.types import SearchItem, SearchConfig, FilterQueryConfig
#
#
# class CollaborativeEngine(FilteredEngine):
#     def __init__(self, db, collection: Collection):
#         self.collection = collection
#         self.db = db
#         self.context = {}
#
#     async def search(self, config: SearchConfig, exclude: List[str], context=None) -> List[SearchItem]:
#         if not config.collaborative:
#             return []
#
#         items_to_search_for: List[Tuple[str, float]] = []
#         # items_to_search_for.extend(
#         #     get_items_from_ofs(self.db, config.collaborative.of, context)
#         # )
#
#         filters = config.filters
#         if isinstance(filters, dict):
#             filters = [FilterQueryConfig(fields=filters)]
#
#         if items_to_search_for:
#             return await self.get_items_seen_by_others(
#                 items_and_weights=items_to_search_for,
#                 limit=self.get_actual_limit_from_config(config),
#                 exclude_external_item_ids=exclude,
#                 filters=filters,
#                 common_events_threshold=config.collaborative.minimum_interactions,
#                 randomize=config.randomize,
#                 export=config.export,
#                 context=context
#             )
#
#         return []
#
#     def get_actual_limit_from_config(self, config):
#         limit = config.limit
#         if config.rank and config.rank.topn and config.rank.topn > limit:
#             limit = config.rank.topn
#
#         return limit
#
#     def get_vectors_of_events_for_user(self, external_person_ids) -> List[Tuple[List[int], float]]:
#         external_item_ids = get_external_item_ids_of_events_for_user(self.db, external_person_ids)
#         weights = {
#             item[0]: item[1] for item in external_item_ids
#         }
#
#         items = Item.objects(self.db).filter(
#             Item.external_id.in_([item[0] for item in external_item_ids])
#         )
#         vectors_of_items = [
#             (item.vector, weights[item.external_id]) for item in items
#         ]
#         return vectors_of_items
#
#     async def get_items_seen_by_others(
#             self,
#             items_and_weights: List[Tuple[str, float]],
#             exclude_external_item_ids: List[Union[int, str]] = None,
#             offset=0,
#             limit=10,
#             filters: List[Union[FilterQueryConfig]] = None,
#             common_events_threshold=2,
#             randomize=False,
#             export=None,
#             context=None
#     ):
#         external_item_ids = [item[0] for item in items_and_weights]
#
#         exclude_external_ids = (exclude_external_item_ids or []) + external_item_ids
#
#         all_where_clauses = []
#         all_where_params = {}
#
#         if filters:
#             filters_query, filter_params = await self.build_sql_filters(filters)
#             if filters_query:
#                 all_where_clauses.append(filters_query)
#             all_where_params.update(filter_params)
#
#         query_params = {
#             "external_item_ids": external_item_ids,
#             "exclude_ids": exclude_external_ids or [],
#             "offset": offset,
#             "limit": limit,
#             "common_events_threshold": common_events_threshold,
#         }
#
#         query_params.update(all_where_params)
#
#         all_where_clauses.append(
#             "common_events_count >= :common_events_threshold"
#         )
#
#         if randomize:
#             order_by = "random()"
#         else:
#             order_by = "common_events_count desc"
#
#         query = text(
#             """
#                 WITH relevant_users AS (
#                     SELECT person_external_id
#                     FROM event
#                     WHERE item_external_id = any(:external_item_ids)
#                 ),
#                 filtered_events AS (
#                     SELECT item_external_id, COUNT(*) AS common_events_count
#                     FROM event
#                     WHERE person_external_id IN (SELECT person_external_id FROM relevant_users)
#                     AND not item_external_id = any(:exclude_ids)
#                     GROUP BY item_external_id
#                 )
#                 SELECT item_external_id, common_events_count
#                 FROM filtered_events join item on item.external_id = filtered_events.item_external_id
#                 {where_clauses}
#                 ORDER BY {order_by}
#                 LIMIT :limit OFFSET :offset;
#             """.format(
#                 where_clauses=f"where {' and '.join(all_where_clauses)}" if all_where_clauses else "",
#                 order_by=order_by
#             )
#         ).params(query_params)
#
#         searched_items = self.db.execute(query).all()
#
#         if not searched_items:
#             return []
#
#         items = Item.objects(self.db).filter(
#             Item.external_id.in_([i.item_external_id for i in searched_items])
#         )
#         items_by_id = {item.external_id: item for item in items}
#         counts_by_id = {
#             i.item_external_id: i.common_events_count for i in searched_items
#         }
#         max_count = max(counts_by_id.values())
#
#         search_items = []
#         for rec in searched_items:
#             db_item = items_by_id.get(rec.item_external_id)
#             if not db_item:
#                 continue
#
#             score = counts_by_id[rec.item_external_id] / max_count
#
#             if export is None:
#                 exported_value = db_item.fields
#             else:
#                 if isinstance(export, str):
#                     exported_value = db_item.fields.get(export)
#                 else:
#                     exported_value = {
#                         field: db_item.fields.get(field) for field in export
#                     }
#
#             search_items.append(
#                 SearchItem(
#                     id=db_item.external_id,
#                     fields=db_item.fields or {},
#                     score=score,
#                     exported=exported_value
#                 )
#             )
#
#         return search_items
