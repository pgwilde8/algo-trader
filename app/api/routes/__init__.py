# API routes module
# Import all route routers here and export them

from .news_avoidance import router as news_avoidance_router

__all__ = [
    "news_avoidance_router",
]
