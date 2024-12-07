import time

from sqlalchemy.orm import Session
from typing import Union

from app.api.autocomplete.types import AutocompleteRequest, AutocompleteResponse, AutocompleteResponseError
from app.api.deps import get_database, get_organization
from app.core.autocompletor.autocompletor import AutoCompletor
from app.logger import logger
from app.models.organization import Organization
from fastapi import APIRouter, HTTPException, Depends

from app.resources.database import m

router = APIRouter()


@router.post("/api/autocomplete", response_model=AutocompleteResponse)
async def autocomplete(
        autocomplete_request: AutocompleteRequest,
        db: Session = Depends(get_database),
        organization: Organization = Depends(get_organization),
) -> Union[AutocompleteResponse, AutocompleteResponseError]:
    begin = time.time()

    collection = m.Collection.objects(db).get_or_create(
        autocomplete_request.collection,
        organization
    )

    logger.info(f"Received suggestion request: {autocomplete_request}")

    autocompletor = AutoCompletor(
        collection=collection,
        db=db,
        config=autocomplete_request.config
    )

    suggestions = await autocompletor.autocomplete()

    took_ms = int((time.time() - begin) * 1000)

    return AutocompleteResponse(suggestions=suggestions, took_ms=took_ms)
