from app.db.session import Database
from app.easytests.clients import AsyncRequestApiClient
from app.easytests.config import EasyTestConfig
from app.main import app

with Database() as db:
    nextlike_easytest_config = EasyTestConfig(
        app=app, base_url="http://localhost:80", client=AsyncRequestApiClient, db = db
    )
