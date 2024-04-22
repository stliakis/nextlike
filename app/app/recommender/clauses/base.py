from app.recommender.clauses.collaborative import PersonItemsClause, ItemToItemsClause
from app.recommender.clauses.similarity import PersonToVectorClause, ItemToVectorClause, FieldsToVectorClause, \
    PromptToVectorClause


def get_items_from_ofs(db, ofs):
    items = []
    clauses = [
        PersonItemsClause,
        ItemToItemsClause
    ]

    for of in ofs:
        for Clause in clauses:
            clause = Clause.from_of(db, of)
            if clause:
                items.extend(clause.get_items())

    return items


def get_vectors_from_ofs(db, ofs):
    vectors = []
    clauses = [
        PersonToVectorClause,
        ItemToVectorClause,
        FieldsToVectorClause,
        PromptToVectorClause
    ]

    for of in ofs:
        for Clause in clauses:
            clause = Clause.from_of(db, of)
            if clause:
                vectors.extend(clause.get_vectors())

    return vectors


def get_item_ids_from_ofs(db, ofs):
    return [item[0] for item in get_items_from_ofs(db, ofs)]
