from pydantic import BaseModel


class IndexerResultItem(BaseModel):
    id: str
    description: str
    similarity: float
