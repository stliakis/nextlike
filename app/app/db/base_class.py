from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, TypeVar, Union

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Query
from sqlalchemy.orm.attributes import flag_modified

from app.settings import get_settings
from app.db.session import Database
from app.utils.base import dictify_model
from app.utils.logging import log
from app.utils.base import camel_to_snake


@as_declarative()
class BaseAlchemyModel(object):
    id: Any
    __name__: str
    Index = None

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return camel_to_snake(cls.__name__)

    def flush(self, db=None):
        if not db and not self.db:
            raise Exception("You need to pass db if you just created the object")

        db = db or self.db
        db.add(self)
        db.flush()
        db.commit()
        db.refresh(self)
        return self

    @property
    def db(self):
        return self._sa_instance_state.session

    def flag_modified(self, field):
        flag_modified(self, field)

    def set(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        return self

    @classmethod
    def create_objects_manager(cls, Manager, db=None):
        if db:
            return Manager(Model=cls, db=db)
        else:
            with Database() as db:
                return Manager(Model=cls, db=db)

    def to_dict(self):
        if hasattr(self, "PydanticModel"):
            return dictify_model(self, self.PydanticModel)
        else:
            return None

    def delete(self, db=None, commit=False):
        db = db or self.db
        db.delete(self)
        if commit:
            db.commit()
            db.flush()


ModelType = TypeVar("ModelType", bound=BaseAlchemyModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class ObjectBulkCreator(object):
    def __init__(self, db, Model=None, bulk_size=1000, flush_after_seconds=None):
        self.db = db
        self.bulk_size = bulk_size
        self.Model = Model
        self.objects = []
        self.flush_after_seconds = flush_after_seconds
        self.last_flush = 0

    async def create(self, **kwargs):
        self.objects.append(kwargs)
        await self.flush_if_needed()
        return self

    async def flush_if_needed(self):
        # if get_settings().is_testing():
        #     self.flush()
        #     return self

        needs_to_flush = False
        if len(self.objects) > self.bulk_size:
            needs_to_flush = True

        if self.flush_after_seconds:
            millis_after_last_flush = (time.time() - self.last_flush)
            if millis_after_last_flush > self.flush_after_seconds:
                needs_to_flush = True

        if needs_to_flush:
            if len(self.objects) > 0:
                await self.flush()

            self.last_flush = time.time()
        return self

    async def flush(self):
        if not self.Model:
            raise NotImplementedError()

        for obj in self.objects:
            self.db.add(self.Model().set(**obj))
        self.db.flush()
        self.objects = []


class BaseModelManager(object):
    ObjectBulkCreator = ObjectBulkCreator

    def __init__(self, Model, db):
        self.Model = Model
        self.db = db

    def get(self, id: Any) -> Optional[ModelType]:
        if not id:
            return None
        return self.db.query(self.Model).filter(self.Model.id == id).first()

    @property
    def select(self):
        return self.db.query

    def filter(self, *args, **kwargs) -> Query:
        return self.db.query(self.Model).filter(*args, **kwargs)

    def filter_by(self, *args, **kwargs) -> Query:
        return self.db.query(self.Model).filter_by(*args, **kwargs)

    def merge(self, obj):
        return self.db.merge(obj)

    def distinct(self, *args, **kwargs) -> Query:
        return self.db.query(self.Model).distinct(*args, **kwargs)

    def get_multi(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        return self.db.query(self.Model).offset(skip).limit(limit).all()

    def in_(self, values, key="id"):
        if not values:
            log("debug", "empty values, passing [-1]")
            values = [-1]

        rows = self.filter(getattr(self.Model, key).in_(values)).all()
        final_rows = []
        for value in values:
            for row in rows:
                if getattr(row, key) == value:
                    final_rows.append(row)
                    break
        return final_rows

    def create(self, obj_in: CreateSchemaType = None, **kwargs) -> ModelType:
        if obj_in:
            obj_in_data = jsonable_encoder(obj_in)
            db_obj = self.Model(**obj_in_data)  # type: ignore
        elif kwargs:
            db_obj = self.Model(**kwargs)  # type: ignore
        else:
            raise Exception("Either obj_in or kwargs are required")

        self.db.add(db_obj)
        self.db.flush()
        self.db.refresh(db_obj)
        return db_obj

    def update(
            self, db_obj: ModelType, obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        self.db.add(db_obj)
        self.db.flush()
        self.db.refresh(db_obj)
        return db_obj

    def remove(self, id: int) -> ModelType:
        obj = self.db.query(self.Model).get(id)
        self.db.delete(obj)
        self.db.flush()
        return obj

    def get_bulk_creator(self, **kwargs) -> ObjectBulkCreator:
        return self.ObjectBulkCreator(self.db, self.Model, **kwargs)

    def delete_all(self):
        self.db.query(self.Model).delete()
