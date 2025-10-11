"""
Assignment routes - centralized imports
"""
from application.features.assignments.routes.assignment_query_routes import router as query_router
from application.features.assignments.routes.assignment_create_routes import router as create_router
from application.features.assignments.routes.assignment_update_routes import router as update_router
from application.features.assignments.routes.assignment_export_routes import router as export_router

__all__ = [
    "query_router",
    "create_router",
    "update_router",
    "export_router",
]
