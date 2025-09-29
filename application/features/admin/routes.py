from fastapi import APIRouter, Depends

from application.features.auth.permissions import require_admin_only_access

router = APIRouter()

@router.get("/health", tags=["Admin"])
def admin_health(_: dict = Depends(require_admin_only_access)):
    return {"status": "ok"}
