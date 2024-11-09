from datetime import datetime
from typing import Union

from pydantic import BaseModel


class ItemsFieldSchema(BaseModel):
    id: int
    collection_id: int
    field_name: str
    field_label: str
    created: Union[datetime, None]
    last_update: Union[datetime, None]
    type: str
