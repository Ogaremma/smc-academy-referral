from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.referral import router as referral_router
from app.api.user import router as user_router
from app.api.webhooks import router as webhooks_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(user_router)
api_v1_router.include_router(webhooks_router)

# Main router combining API v1 and public referral routes
main_router = APIRouter()
main_router.include_router(api_v1_router)
main_router.include_router(referral_router)
