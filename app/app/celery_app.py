from celery import Celery

celery_app = Celery("nextlike", broker="redis://redis:6379/0")
celery_app.conf.update(
    task_serializer="pickle",
    result_serializer="pickle",
    event_serializer="json",
    accept_content=["application/json", "application/x-python-serialize"],
    result_accept_content=["application/json", "application/x-python-serialize"],
)
celery_app.autodiscover_tasks(["app.tasks.items"])
celery_app.autodiscover_tasks(["app.tasks.events"])
celery_app.autodiscover_tasks(["app.tasks.beat"])

celery_app.conf.beat_schedule = {
    "cleanup_events": {
        "task": "app.tasks.beat.cleanup_events",
        "schedule": 3600
    },
    "cleanup_search_history": {
        "task": "app.tasks.beat.cleanup_search_history",
        "schedule": 3600
    },
    "cleanup_lone_person_events": {
        "task": "app.tasks.beat.cleanup_lone_person_events",
        "schedule": 3600
    },
    "cleanup_events_limit_per_user": {
        "task": "app.tasks.beat.cleanup_events_limit_per_user",
        "schedule": 60 * 10
    },
    "indexers_cleanup": {
        "task": "app.tasks.beat.indexers_cleanup",
        "schedule": 60
    },
    "clean_dirty_items": {
        "task": "app.tasks.beat.clean_dirty_items",
        "schedule": 60
    }
}

CELERY_ACCEPT_CONTENT = ["pickle"]
