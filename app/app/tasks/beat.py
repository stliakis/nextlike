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
        events = (
            m.Event.objects(db)
            .filter(
                m.Event.created
                < datetime.datetime.now()
                - datetime.timedelta(
                    seconds=parse_time_string(get_settings().EVENTS_CLEANUP_AFTER)
                )
            )
            .yield_per(1000)
        )

        for i, event in enumerate(events):
            event.delete(db)
            if i % 1000 == 0:
                db.flush()

        db.flush()


@celery_app.task
def cleanup_recommendations_history():
    with Database() as db:
        recommendations = (
            m.SearchHistory.objects(db)
            .filter(
                m.SearchHistory.created
                < datetime.datetime.now()
                - datetime.timedelta(
                    seconds=parse_time_string(
                        get_settings().RECOMMENDATIONS_HISTORY_CLEANUP_AFTER
                    )
                )
            )
            .yield_per(1000)
        )

        for i, recommendation in enumerate(recommendations):
            recommendation.delete(db)
            if i % 1000 == 0:
                db.flush()

        db.flush()


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
                                     where created < CURRENT_DATE - INTERVAL '%i days'
                                     group by person_external_id
                                     having count(*) <= %i)
        """
                % (
                    get_settings().EVENTS_CLEANUP_LONE_EVENTS_AFTER,
                    get_settings().EVENTS_CLEANUP_LONE_EVENTS_MIN_COUNT,
                )
            )
        )
