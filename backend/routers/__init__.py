"""kill-prop API routers.

Exposes all router objects for easy mounting:

    from backend.routers import articles, events, review
"""

from backend.routers.articles import router as articles_router
from backend.routers.events import router as events_router
from backend.routers.review import router as review_router

__all__ = ["articles_router", "events_router", "review_router"]
