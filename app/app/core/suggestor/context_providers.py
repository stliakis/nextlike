from app.core.searcher.types import SearchConfig


class ContextProvider(object):
    type = None

    def get_context(self) -> str:
        raise NotImplementedError

    @classmethod
    def get_provider(cls, db, collection, context):
        for Provider in [
            ItemsContextProvider
        ]:
            provider_instance = Provider.from_context(db, collection, context)
            if provider_instance:
                return provider_instance


class ItemsContextProvider(ContextProvider):
    type = "items"

    def __init__(self, db, collection, search_config: SearchConfig, context_title=None):
        self.db = db
        self.collection = collection
        self.search_config = search_config
        self.context_title = context_title

    @classmethod
    def from_context(cls, db, collection, context):
        if context.type == "items":
            return cls(
                db=db,
                collection=collection,
                search_config=context.search,
                context_title=context.context_title
            )

    def get_context(self) -> str:
        return f"""{self.context_title or 'items'}:
        Apartment in giannitsa
        Opel corsa giannitsa
        Office space max 3000 euro
        Opel corsa πωληση
        Χειμερινά ελαστικά για opel corsa
        Διαμέρισμα στο κολονακι έως 50k
        Διαμεριμα μέχρι 300 ευρώ ενοικιο
        """
