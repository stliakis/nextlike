from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.settings import get_settings

engine = create_engine(get_settings().POSTGRES_CONNECTION_STRING, pool_pre_ping=True, pool_size=20, max_overflow=0)
SessionLocal = sessionmaker(autoflush=False, bind=engine)


class Database(object):
    def __init__(self):
        pass

    def __enter__(self):
        self.db = SessionLocal()
        return self.db

    def __exit__(self, *args, **kwargs):
        self.db.close()
