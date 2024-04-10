from typing import Union

from pydantic import BaseModel


class PaginationModel(BaseModel):
    total: int
    size: int
    next: Union[str, None]
