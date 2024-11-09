import datetime

from pydantic import BaseModel


class EventSchema(BaseModel):
    event_type: str
    item_external_id: str
    person_external_id: str
    date: datetime.datetime
