import datetime

from sqlalchemy import text

from app.celery_app import celery_app
from app.db.session import Database
from app.resources.database import m
from app.settings import get_settings
from app.utils.base import parse_time_string


@celery_app.task
def cleanup_events():
    with Database() as db:
        db.execute(
            text(
                """
                delete
                from event
                where created < CURRENT_DATE - INTERVAL '%i seconds'
                """
                % (
                    parse_time_string(get_settings().EVENTS_CLEANUP_AFTER)
                )
            )
        )


@celery_app.task
def cleanup_recommendations_history():
    with Database() as db:
        db.execute(
            text(
                """
                delete
                from search_history
                where created < CURRENT_DATE - INTERVAL '%i seconds'
                """
                % (
                    parse_time_string(get_settings().RECOMMENDATIONS_HISTORY_CLEANUP_AFTER)
                )
            )
        )


@celery_app.task
def cleanup_lone_person_events():
    with Database() as db:
        db.execute(
            text(
                """
                delete
                from event
                where person_external_id in (select person_external_id
                                             from event
                                             where created < CURRENT_DATE - INTERVAL '%i seconds'
                                             group by person_external_id
                                             having count(*) <= %i)
                """ % (
                    parse_time_string(get_settings().EVENTS_CLEANUP_LONE_EVENTS_AFTER),
                    get_settings().EVENTS_CLEANUP_LONE_EVENTS_MIN_COUNT,
                )
            )
        )
