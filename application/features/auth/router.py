"""
Refactored auth routes - now imports from separate modules for better organization.
"""
from fastapi import APIRouter
from fastapi.security import OAuth2PasswordBearer

from application.features.auth.routes.email_routes import router as email_router
from application.features.auth.routes.google_routes import router as google_router
from application.features.auth.routes.gatech_routes import router as gatech_router
from application.features.auth.routes.token_routes import router as token_router
from application.features.auth.routes.user_routes import router as user_router

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router.include_router(email_router, tags=["Email Authentication"])
router.include_router(google_router, tags=["Google OAuth"])
router.include_router(gatech_router, tags=["Georgia Tech SAML"])
router.include_router(token_router, tags=["Token Management"])
router.include_router(user_router, prefix="/user", tags=["User Self-Service"])