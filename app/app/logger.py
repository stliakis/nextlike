import logging

from logging.config import dictConfig

from app.settings import LogSettings


def initialize_logger():
    dictConfig(LogSettings().dict())


logger = logging.getLogger("nextlike")
