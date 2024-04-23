import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.requests import Request

from app.logger import initialize_logger
from app.settings import get_settings

from app.api.collections import collections
from app.api.events import events
from app.api.items import items
from app.api.recommendations import recommendations

load_dotenv()

initialize_logger()

os.environ["OPENAI_API_KEY"] = get_settings().OPENAI_API_KEY

app = FastAPI(redoc_url="/docs", docs_url="/docs/swagger")


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    print(f"[{request.url}] took {round((time.time() - start_time) * 1000)}ms")
    return response


app.include_router(items.router)
app.include_router(events.router)
app.include_router(collections.router)
app.include_router(recommendations.router)


@app.get("/health")
def health():
    return {"message": "Hi. I'm alive!"}
