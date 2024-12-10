from typing import List

from app.core.searcher.clauses.filter_clauses import FieldsFilterClause
from app.core.searcher.clauses.item_clauses import PersonItemsClause, ItemToItemsClause, RecommendationsItemsClause
from app.core.searcher.clauses.text_clauses import TextSearchClause
from app.core.searcher.clauses.vector_clauses import PersonToVectorClause, ItemToVectorClause, FieldsToVectorClause, \
    PromptToVectorClause, EmbeddingsClause
from app.core.types import TextClauseQuery, FieldsClause


def get_items_from_ofs(db, ofs, context):
    items = []
    clauses = [
        PersonItemsClause,
        ItemToItemsClause,
        RecommendationsItemsClause
    ]

    for of in ofs:
        for Clause in clauses:
            clause = Clause.from_of(db, of, context)
            if clause:
                items.extend(clause.get_items())

    return items


def get_vectors_from_ofs(db, similarity_engine, clauses, context: dict):
    vectors = []
    available_clause_classes = [
        PersonToVectorClause,
        ItemToVectorClause,
        FieldsToVectorClause,
        PromptToVectorClause,
        EmbeddingsClause
    ]

    for clause in clauses:
        for Clause in available_clause_classes:
            clause_object = Clause.from_of(db, similarity_engine, clause, context)
            if clause_object:
                vectors.extend(clause_object.get_vectors())

    return vectors


def get_text_queries_from_ofs(db, similarity_engine, ofs, context: dict):
    queries: List[TextClauseQuery] = []
    clauses = [
        TextSearchClause
    ]

    for of in ofs:
        for Clause in clauses:
            clause = Clause.from_of(db, similarity_engine, of, context)
            if clause:
                queries.extend(clause.get_queries())

    return queries


def get_filter_queries_from_ofs(db, similarity_engine, ofs, context: dict):
    queries: List[TextClauseQuery] = []
    clauses = [
        FieldsFilterClause
    ]

    for of in ofs:
        for Clause in clauses:
            clause = Clause.from_of(db, similarity_engine, of, context)
            if clause:
                queries.extend(clause.get_filter_queries())

    return queries


def get_item_ids_from_ofs(db, ofs, context):
    return [item[0] for item in get_items_from_ofs(db, ofs, context)]
