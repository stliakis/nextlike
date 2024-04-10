from datetime import datetime
from typing import Union, List

from pydantic import BaseModel

from app.utils.lists import Pagination


class LogSchema(BaseModel):
    organization_id: int
    collection_id: int
    message: Union[str, None]
    created: datetime
    log_type: str


class LogsListResponse(BaseModel):
    pagination: Pagination.PydanticModel
    rows: List[LogSchema]


class LogsResponse(BaseModel):
    logs: LogsListResponse
