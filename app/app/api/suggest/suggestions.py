import time

from sqlalchemy.orm import Session
from typing import Union
from app.api.deps import get_database, get_organization
from app.api.suggest.types import SuggestionsResponse, SuggestionsRequest, SuggestionResponseError
from app.core.suggestor.suggestor import Suggestor
from app.exceptions.items import ItemNotFound
from app.logger import logger
from app.models.organization import Organization
from fastapi import APIRouter, HTTPException, Depends

router = APIRouter()


@router.post("/api/suggest", response_model=SuggestionsResponse)
async def search(
        suggestions_request: SuggestionsRequest,
        db: Session = Depends(get_database),
        organization: Organization = Depends(get_organization),
) -> Union[SuggestionsResponse, SuggestionResponseError]:
    begin = time.time()

    logger.info(f"Received suggestion request: {suggestions_request}")

    suggestor = Suggestor(
        organization,
        db=db,
        config=suggestions_request.config
    )

    suggestions = await suggestor.suggest()

    took_ms = int((time.time() - begin) * 1000)

    return SuggestionsResponse(suggestions=suggestions, took_ms=took_ms)
