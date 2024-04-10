from sqlalchemy import text
from typing import List, Union

from app.models.collection import Collection
from app.models.recommendations.items.item import Item
from app.recommender.types import RecommendedItem
from app.resources.database import m
from app.utils.base import listify
from app.utils.json_filter_query import build_query_string_and_params


class CollaborativeEngine(object):
    def __init__(self, db, collection: Collection):
        self.collection = collection
        self.db = db

    def get_external_item_ids_of_users(self, external_person_ids):
        events = m.Event.objects(self.db).select(m.Event.item_external_id).filter(
            m.Event.person_external_id.in_(external_person_ids)
        )
        external_item_ids = [map(str, event.item_external_id) for event in events]
        return external_item_ids

    def get_items_seen_by_others(
            self,
            external_item_ids: List[str],
            exclude_external_item_ids: List[Union[int, str]] = None,
            offset=0,
            limit=10,
            filters: Union[dict, None] = None,
            common_events_threshold=2,
            randomize=False
    ):
        exclude_external_ids = (exclude_external_item_ids or []) + external_item_ids

        all_where_clauses = []
        all_where_params = {}

        if filters:
            filters_query, filter_params = build_query_string_and_params(
                "fields", filters
            )
            all_where_clauses.append(filters_query)
            all_where_params.update(filter_params)

        query_params = {
            "external_item_ids": external_item_ids,
            "exclude_ids": exclude_external_ids or [],
            "offset": offset,
            "limit": limit,
            "common_events_threshold": common_events_threshold,
        }

        query_params.update(all_where_params)

        all_where_clauses.append(
            "interaction_count >= :common_events_threshold"
        )

        if randomize:
            order_by = "random()"
        else:
            order_by = "interactions_count desc"

        query = text(
            """
                WITH relevant_users AS (
                    SELECT person_external_id
                    FROM event
                    WHERE item_external_id = any(:external_item_ids)
                ),
                filtered_events AS (
                    SELECT item_external_id, COUNT(*) AS common_events_count
                    FROM event
                    WHERE person_external_id IN (SELECT person_external_id FROM relevant_users)
                    AND item_external_id != any(:exclude_ids)
                    GROUP BY item_external_id
                )
                SELECT item_external_id, common_events_count
                FROM filtered_events join item on item.external_id = filtered_events.item_external_id
                {where_clauses}
                ORDER BY {order_by}
                LIMIT :limit OFFSET :offset;
            """.format(
                where_clauses=f"where {' and '.join(all_where_clauses)}" if all_where_clauses else "",
                order_by=order_by
            )
        ).params(query_params)

        recommended_items = self.db.execute(query).all()

        if not recommended_items:
            return []

        items = Item.objects(self.db).filter(
            Item.external_id.in_([i.item_external_id for i in recommended_items])
        )
        items_by_id = {item.external_id: item for item in items}
        counts_by_id = {
            i.item_external_id: i.interaction_count for i in recommended_items
        }
        max_count = max(counts_by_id.values())

        recommendations = []
        for rec in recommended_items:
            db_item = items_by_id.get(rec.item_external_id)
            if not db_item:
                continue

            score = counts_by_id[rec.item_external_id] / max_count

            recommendations.append(
                RecommendedItem(
                    external_id=db_item.external_id,
                    id=db_item.id,
                    fields=db_item.fields or {},
                    score=score,
                )
            )

        return recommendations
