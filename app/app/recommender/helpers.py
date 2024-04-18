from typing import List, Tuple

from app.resources.database import m
from app.utils.base import time_string_to_datetime_from_now


def get_vectors_of_events_for_user(
        db, external_person_ids, time, limit
) -> List[Tuple[List[int], float]]:
    external_item_ids = get_external_item_ids_of_events_for_user(
        db=db, external_person_ids=external_person_ids, time=time, limit=limit
    )
    weights = {item[0]: item[1] for item in external_item_ids}

    items = m.Item.objects(db).filter(
        m.Item.external_id.in_([item[0] for item in external_item_ids])
    )
    vectors_of_items = [(item.vector, weights[item.external_id]) for item in items if item.vector]
    return vectors_of_items


def get_external_item_ids_of_events_for_user(
        db, external_person_ids, time=None, limit=None
) -> List[Tuple[str, float]]:
    events = (
        m.Event.objects(db)
        .select(m.Event.item_external_id, m.Event.weight)
        .filter(m.Event.person_external_id.in_(external_person_ids))
    )

    if time:
        events = events.filter(m.Event.created > time_string_to_datetime_from_now(time))

    if limit:
        events = events.limit(limit)

    return [(event.item_external_id, event.weight) for event in events]
