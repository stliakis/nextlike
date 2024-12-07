from app.core.types import FilterQueryConfig


class FieldsFilterClause(object):
    def __init__(self, db, similarity_engine, fields, context):
        self.db = db
        self.similarity_engine = similarity_engine
        self.fields = fields
        self.context = context

    @classmethod
    def from_of(cls, db, similarity_engine, of, context):
        if hasattr(of, 'fields'):
            return cls(db, similarity_engine, of.fields, context)

    def get_filter_queries(self):
        return FilterQueryConfig(fields=self.fields)
