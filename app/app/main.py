import os
from dotenv import load_dotenv
from fastapi import FastAPI

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

app.include_router(items.router)
app.include_router(events.router)
app.include_router(collections.router)
app.include_router(recommendations.router)


@app.get("/health")
def health():
    return {"message": "Hi. I'm alive!"}
