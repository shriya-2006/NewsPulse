"""
ORM model package.

Every model must be imported here so that `Base.metadata` (used by
Alembic/`create_all`) is aware of it — importing app.models is enough
to register the full schema.
"""

from app.models.user import PasswordResetToken, User  # noqa: F401
from app.models.tag import CustomTag  # noqa: F401
from app.models.search_history import SearchHistory  # noqa: F401
from app.models.report import Article, Report, report_articles  # noqa: F401
from app.models.newspaper import Newspaper, NewspaperEdition  # noqa: F401
from app.models.cached_search import CachedSearch, cached_search_articles  # noqa: F401
