import datetime
from typing import List

from pydantic import BaseModel


class ItemSchema(BaseModel):
    external_id: str
    id: int
    created: datetime.datetime
    fields: List[dict]
