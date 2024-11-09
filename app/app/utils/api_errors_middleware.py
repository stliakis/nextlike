from pprint import pprint

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Any

from app.utils.logging import log


# Function to format Pydantic errors
def format_pydantic_errors(errors: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    formatted_errors = {}
    for error in errors:
        loc = ".".join(map(str, error['loc']))  # Dot notation for nested fields
        formatted_errors[loc] = {
            "error": "validation_error",
            "message": error['msg']
        }

    log("error", f"Validation error: ", formatted_errors)

    return formatted_errors


# Custom error handler for RequestValidationError
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    formatted_errors = format_pydantic_errors(exc.errors())
    return JSONResponse(status_code=422, content=formatted_errors)


# Custom error handler for ValidationError outside of request body validation
async def validation_exception_handler(request: Request, exc: ValidationError):
    formatted_errors = format_pydantic_errors(exc.errors())
    return JSONResponse(status_code=422, content=formatted_errors)
