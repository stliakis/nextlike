from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import Database
from app.resources.database import m
from app.settings import get_settings


def get_database():
    with Database() as db:
        yield db


def get_organization(db: Session = Depends(get_database)):
    if not get_settings().ORGANIZATION:
        raise Exception("Missing global organization name")

    return m.Organization.objects(db).get_or_create(get_settings().ORGANIZATION)
