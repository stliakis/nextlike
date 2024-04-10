from app.settings import get_settings
from elasticsearch import Elasticsearch


def get_elastic():
    return Elasticsearch(hosts=[get_settings().ELASTIC_SEARCH_HOST])
