import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import ValidationError
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from app.api import base
from app.api.suggest import suggestions
from app.logger import initialize_logger
from app.utils.api_errors_middleware import \
    validation_exception_handler, request_validation_exception_handler
from app.utils.logging import log
from app.settings import get_settings

from app.api.collections import collections
from app.api.events import events
from app.api.items import items
from app.api.search import search
from app.api.aggregations import aggregations

load_dotenv()

initialize_logger()

os.environ["OPENAI_API_KEY"] = get_settings().OPENAI_API_KEY

app = FastAPI(redoc_url="/docs", docs_url="/docs/swagger")

app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    log("info", f"[{request.url}] took {round((time.time() - start_time) * 1000)}ms")
    return response


app.include_router(items.router)
app.include_router(events.router)
app.include_router(collections.router)
app.include_router(search.router)
app.include_router(suggestions.router)
app.include_router(aggregations.router)

app.include_router(base.router)


@app.get("/health")
def health():
    return {"message": "Hi. I'm alive!"}
