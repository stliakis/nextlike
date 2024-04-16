# Import all the models, so that Base has them before being
# imported by Alembic
from app.db.base_class import BaseAlchemyModel  # noqa
from app.models.collection import Collection  # noqa
from app.models.recommendations.items.item import *  # noqa
from app.models.recommendations.events.event import *  # noqa
from app.models.recommendations.persons.person import *  # noqa
from app.models.recommendations.persons.persons_fields import *  # noqa
from app.models.recommendations.items.items_field import *  # noqa
from app.models.recommendations.history.search_history import *  # noqa
