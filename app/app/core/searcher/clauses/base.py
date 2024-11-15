from app.core.searcher.clauses.item_clauses import PersonItemsClause, ItemToItemsClause, RecommendationsItemsClause
from app.core.searcher.clauses.text_clauses import TextSearchClause
from app.core.searcher.clauses.vector_clauses import PersonToVectorClause, ItemToVectorClause, FieldsToVectorClause, \
    PromptToVectorClause, EmbeddingsClause


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


def get_vectors_from_ofs(db, similarity_engine, ofs, context: dict):
    vectors = []
    clauses = [
        PersonToVectorClause,
        ItemToVectorClause,
        FieldsToVectorClause,
        PromptToVectorClause,
        EmbeddingsClause
    ]

    for of in ofs:
        for Clause in clauses:
            clause = Clause.from_of(db, similarity_engine, of, context)
            if clause:
                vectors.extend(clause.get_vectors())

    return vectors


def get_queries_from_ofs(db, similarity_engine, ofs, context: dict):
    queries = []
    clauses = [
        TextSearchClause
    ]

    for of in ofs:
        for Clause in clauses:
            clause = Clause.from_of(db, similarity_engine, of, context)
            if clause:
                queries.extend(clause.get_queries())

    return queries


def get_item_ids_from_ofs(db, ofs, context):
    return [item[0] for item in get_items_from_ofs(db, ofs, context)]
