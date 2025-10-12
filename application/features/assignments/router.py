"""
Assignment routes aggregator - imports from separate modules for better organization.
"""
from fastapi import APIRouter

from application.features.assignments.routes.assignment_query_routes import router as query_router
from application.features.assignments.routes.assignment_create_routes import router as create_router
from application.features.assignments.routes.assignment_update_routes import router as update_router
from application.features.assignments.routes.assignment_export_routes import router as export_router

router = APIRouter()

# Include all sub-routers with appropriate tags
router.include_router(query_router, tags=["Assignment Queries"])
router.include_router(create_router, tags=["Assignment Creation"])
router.include_router(update_router, tags=["Assignment Updates"])
router.include_router(export_router, tags=["Assignment Export"])
