from app.db.session import SessionLocal


def get_session():
    return SessionLocal()


class ModelsProxy(object):
    @property
    def Item(self):
        from app.models.search.items.item import Item
        return Item

    @property
    def Person(self):
        from app.models.search.persons.person import Person
        return Person

    @property
    def PersonsField(self):
        from app.models.search.persons.persons_fields import PersonsField
        return PersonsField

    @property
    def Collection(self):
        from app.models.collection import Collection
        return Collection

    @property
    def ItemsField(self):
        from app.models.search.items.items_field import ItemsField
        return ItemsField

    @property
    def Event(self):
        from app.models.search.events.event import Event
        return Event

    @property
    def Organization(self):
        from app.models.organization import Organization
        return Organization

    @property
    def SearchHistory(self):
        from app.models.search.history.search_history import SearchHistory
        return SearchHistory


m = ModelsProxy()
