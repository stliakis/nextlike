import asyncio
import datetime

from sqlalchemy import text

from app.celery_app import celery_app
from app.core.indexers.redis_indexer import RedisIndexer
from app.core.indexers.sql_indexer import SQLIndexer
from app.db.session import Database
from app.resources.database import m
from app.settings import get_settings
from app.utils.base import parse_time_string
from app.utils.logging import log
from app.utils.temporal_lock import RedisTemporalLock


@celery_app.task
async def cleanup_events():
    async with RedisTemporalLock("cleanup_events_limit_per_user", expire=3600 * 3) as unlocked:
        if unlocked:
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
async def cleanup_search_history():
    async with RedisTemporalLock("cleanup_events_limit_per_user", expire=3600 * 3) as unlocked:
        if unlocked:
            with Database() as db:
                db.execute(
                    text(
                        """
                        delete
                        from search_history
                        where created < CURRENT_DATE - INTERVAL '%i seconds'
                        """
                        % (
                            parse_time_string(get_settings().SEARCH_HISTORY_CLEANUP_AFTER)
                        )
                    )
                )


@celery_app.task
async def cleanup_lone_person_events():
    async with RedisTemporalLock("cleanup_events_limit_per_user", expire=3600 * 3) as unlocked:
        if unlocked:
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


@celery_app.task
async def cleanup_events_limit_per_user():
    async with RedisTemporalLock("cleanup_events_limit_per_user", expire=3600 * 3) as unlocked:
        if unlocked:
            with Database() as db:
                db.execute(
                    text(
                        """
                            WITH ranked_events AS (SELECT created,
                                                          person_external_id,
                                                          event_type,
                                                          ROW_NUMBER()
                                                          OVER (PARTITION BY person_external_id, event_type ORDER BY created DESC) AS rn
                                                   FROM event),
                                 events_to_delete AS (SELECT created,
                                                             person_external_id,
                                                             event_type
                                                      FROM ranked_events
                                                      WHERE rn > %i)
                            DELETE
                            FROM event
                                USING
                                    events_to_delete
                            WHERE event.created = events_to_delete.created
                              AND event.person_external_id = events_to_delete.person_external_id
                              AND event.event_type = events_to_delete.event_type;
                        """ % (
                            get_settings().EVENTS_CLEANUP_MAX_PER_PERSON_AND_TYPE
                        )
                    )
                )


@celery_app.task
def indexers_cleanup():
    async def execute():
        async with RedisTemporalLock("indexers_cleanup", expire=3600 * 3) as unlocked:
            if unlocked:
                with Database() as db:
                    await RedisIndexer.cleanup_all(db)
                    await SQLIndexer.cleanup_all(db)

                    collections = m.Collection.objects(db).filter().all()
                    for collection in collections:
                        log("info",
                            "CollectionIndexer[name=%s, indexer=%s] cleaning up" % (
                                collection.name, collection.config.indexer))

                        if collection.name == "classifieds":
                            continue

                        indexer = collection.get_indexer()
                        await indexer.cleanup()

    asyncio.run(execute())
