from pydantic import BaseSettings
from pydantic import BaseModel


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    GROQ_API_KEY: str = None
    DEFAULT_LLM_PROVIDER_AND_MODEL: str = "openai:gpt-4o"
    POSTGRES_CONNECTION_STRING: str
    MEMCACHED_HOST: str = "memcached:11211"
    ENVIRONMENT: str = "production"
    DEFAULT_EMBEDDINGS_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-4o"
    INGEST_BATCH_SIZE: int = 500
    DELETE_BATCH_SIZE: int = 100
    COLLABORATIVE_SHARDS_COUNT: int = 4
    COLLABORATIVE_REPLICAS_COUNT: int = 1
    COLLABORATIVE_MAX_ITEMS_PER_USER: int = 100
    EVENTS_CLEANUP_AFTER: str = "30d"
    RECOMMENDATIONS_HISTORY_CLEANUP_AFTER: str = "3d"
    EVENTS_CLEANUP_LONE_EVENTS_AFTER: str = "24h"
    EVENTS_CLEANUP_LONE_EVENTS_MIN_COUNT: int = 2
    ORGANIZATION: str = "nextlike-org"
    EVENT_TO_RECOMMENDATION_HISTORY_THRESHOLD_MINUTES = 3600 * 10

    def is_testing(self):
        return self.ENVIRONMENT == "testing"


class LogSettings(BaseModel):
    """Logging configuration to be set for the server"""

    LOGGER_NAME: str = "nextlike"
    LOG_FORMAT: str = "%(levelprefix)s | %(asctime)s | %(message)s"
    LOG_LEVEL: str = "DEBUG"

    # Logging config
    version = 1
    disable_existing_loggers = False
    formatters = {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }
    handlers = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    }
    loggers = {
        LOGGER_NAME: {"handlers": ["default"], "level": LOG_LEVEL},
    }


def get_settings() -> Settings:
    return Settings()
