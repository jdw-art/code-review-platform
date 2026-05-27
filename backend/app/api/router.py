from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.menus import router as menus_router
from app.api.routes.me import router as me_router
from app.api.routes.permissions import router as permissions_router
from app.api.routes.roles import router as roles_router
from app.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(me_router)
api_router.include_router(roles_router)
api_router.include_router(permissions_router)
api_router.include_router(menus_router)
api_router.include_router(users_router)
