from .auth import router as auth_router
from .users import router as users_router
from .products import router as products_router
from .posts import router as posts_router
from .sync import router as sync_router
from .me import router as me_router
from .mock_woocommerce import router as mock_woocommerce_router
from .templates import router as templates_router  # ΠΡΟΣΘΗΚΗ

__all__ = [
    "auth_router",
    "users_router",
    "products_router",
    "posts_router",
    "sync_router",
    "me_router",
    "mock_woocommerce_router",
    "templates_router",  # ΠΡΟΣΘΗΚΗ
]
