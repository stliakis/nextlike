import sys

from sqlalchemy import select, text

from app.db.session import Database
from app.models import Item
from app.recommender.collaborative_engine import CollaborativeEngine
from app.recommender.similarity_engine import SimilarityEngine
from app.recommender.types import RecommendedItem
from app.utils.json_filter_query import build_query_string_and_params

