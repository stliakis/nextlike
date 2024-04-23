from app.recommender.clauses.item_clauses import PersonItemsClause, ItemToItemsClause, RecommendationsItemsClause
from app.recommender.clauses.vector_clauses import PersonToVectorClause, ItemToVectorClause, FieldsToVectorClause, \
    PromptToVectorClause


def get_items_from_ofs(db, ofs):
    items = []
    clauses = [
        PersonItemsClause,
        ItemToItemsClause,
        RecommendationsItemsClause
    ]

    for of in ofs:
        for Clause in clauses:
            clause = Clause.from_of(db, of)
            if clause:
                items.extend(clause.get_items())

    return items


def get_vectors_from_ofs(db, similarity_engine, ofs):
    vectors = []
    clauses = [
        PersonToVectorClause,
        ItemToVectorClause,
        FieldsToVectorClause,
        PromptToVectorClause
    ]

    for of in ofs:
        for Clause in clauses:
            clause = Clause.from_of(db, similarity_engine, of)
            if clause:
                vectors.extend(clause.get_vectors())

    return vectors


def get_item_ids_from_ofs(db, ofs):
    return [item[0] for item in get_items_from_ofs(db, ofs)]
