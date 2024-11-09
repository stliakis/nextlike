# Import all the models, so that Base has them before being
# imported by Alembic
from app.db.base_class import BaseAlchemyModel  # noqa
from app.models.collection import Collection  # noqa
from app.models.search.items.item import *  # noqa
from app.models.search.events.event import *  # noqa
from app.models.search.persons.person import *  # noqa
from app.models.search.persons.persons_fields import *  # noqa
from app.models.search.items.items_field import *  # noqa
from app.models.search.history.search_history import *  # noqa
