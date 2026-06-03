from fastapi import APIRouter

from app.api.routes.agent import router as agent_router
from app.api.routes.audit_logs import router as audit_logs_router
from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.integration_webhooks import router as integration_webhooks_router
from app.api.routes.llm_models import router as llm_models_router
from app.api.routes.menus import router as menus_router
from app.api.routes.me import router as me_router
from app.api.routes.member_analytics import router as member_analytics_router
from app.api.routes.notification_bots import router as notification_bots_router
from app.api.routes.permissions import router as permissions_router
from app.api.routes.project_templates import router as project_templates_router
from app.api.routes.projects import router as projects_router
from app.api.routes.review_records import router as review_records_router
from app.api.routes.roles import router as roles_router
from app.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(agent_router)
api_router.include_router(me_router)
api_router.include_router(dashboard_router)
api_router.include_router(integration_webhooks_router)
api_router.include_router(llm_models_router)
api_router.include_router(review_records_router)
api_router.include_router(member_analytics_router)
api_router.include_router(notification_bots_router)
api_router.include_router(audit_logs_router)
api_router.include_router(project_templates_router)
api_router.include_router(projects_router)
api_router.include_router(roles_router)
api_router.include_router(permissions_router)
api_router.include_router(menus_router)
api_router.include_router(users_router)
