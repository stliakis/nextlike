from __future__ import annotations

import sqlalchemy
from sqlalchemy import (
    Column,
    String,
    BigInteger,
    ForeignKey,
    DateTime,
    func,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base_class import BaseAlchemyModel, BaseModelManager
from app.resources.database import m
from app.schemas.search.items_field import ItemsFieldSchema
from app.utils.base import default_ns_id
from app.utils.logging import log


class ItemsField(BaseAlchemyModel):
    PydanticModel = ItemsFieldSchema

    id = Column(BigInteger, primary_key=True, default=default_ns_id)
    collection_id = Column(BigInteger, ForeignKey(m.Collection.id, ondelete="CASCADE"), primary_key=True)
    collection = relationship("Collection")
    field_name = Column(String, nullable=False)
    field_label = Column(String, nullable=False)
    created = Column(DateTime, default=func.now())
    order = Column(BigInteger, nullable=False, default=1)
    type = Column(String, nullable=False)

    __table_args__ = (UniqueConstraint("collection_id", "field_name"),)

    DEFAULT_VALUE_TYPE = "string"

    class Manager(BaseModelManager):
        def create_fields_if_missing(self, collection, fields):
            field_names = fields.keys()

            existing_item_fields = ItemsField.objects(self.db).filter(
                ItemsField.collection_id == collection.id,
                ItemsField.field_name.in_(field_names),
            )

            last_order = max([i.order for i in existing_item_fields] or [0])

            existing = [i.field_name for i in existing_item_fields]

            not_existing = [field for field in field_names if field not in existing]

            if not_existing:
                for field in not_existing:
                    last_order += 1
                    types = fields.get(field) or [ItemsField.DEFAULT_VALUE_TYPE]

                    try:
                        ItemsField().set(
                            collection_id=collection.id,
                            field_name=field,
                            field_label=field,
                            order=last_order,
                            type=types[0],
                        ).flush(self.db)
                    except sqlalchemy.exc.IntegrityError:
                        log("warning", "items_field [%s] exists, skipping" % field)

        def get_fields_of_collection(self, collection_id):
            return (
                ItemsField.objects(self.db)
                .filter(ItemsField.collection_id == collection_id)
                .order_by(ItemsField.order)
            )

    @classmethod
    def find_best_fit_value_type_of_value(cls, value):
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, (int, float)):
            return "number"

        return "string"

    @classmethod
    def objects(cls, db=None) -> Manager:
        return cls.create_objects_manager(cls.Manager, db=db)
