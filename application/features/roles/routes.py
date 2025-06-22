
from fastapi import Depends, APIRouter, HTTPException

from application.features.auth.permissions import require_admin_access

from application.database.mssql_crud_helpers import fetch_all, create_record, update_record, delete_record, fetch_by_id
from application.features.roles.schemas import RoleCreate, RoleResponse, RoleUpdate


router = APIRouter()

@router.get("/", response_model=list[RoleResponse])
async def get_roles(user_data: dict = Depends(require_admin_access)):
    """
    Retrieves and returns a list of all types of roles.
    """
    return fetch_all("Roles")


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role_by_id(role_id: int, user_data: dict = Depends(require_admin_access)):
    """
    Retrieves a specific role by its ID.
    """
    role = fetch_by_id("Roles", role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role



@router.post("/", response_model=RoleResponse)
async def create_role(role_data: RoleCreate, user_data: dict = Depends(require_admin_access)):

    """
    Creates a new role with the provided data.
    """
    new_role = {
        "role_name": role_data.role_name,
        "description": role_data.description
    }

    created_role = create_record("Roles", new_role)

    if not created_role:
        raise HTTPException(status_code=400, detail="Role creation failed")
    return created_role



@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate, 
    user_data: dict = Depends(require_admin_access)
):
    """
    Updates an existing role by its ID with the provided data.
    Only the provided fields will be updated.
    """
    fields_to_update = role_data.dict(exclude_unset=True)
    if not fields_to_update:
        raise HTTPException(status_code=400, detail="No data provided for update")

    role = update_record("Roles", role_id, fields_to_update)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.delete("/{role_id}", response_model=dict)
async def delete_role(role_id: int, user_data: dict = Depends(require_admin_access)):
    """
    Deletes a role by its ID.
    """
    result = delete_record("Roles", role_id)
    if not result:
        raise HTTPException(status_code=404, detail="Role not found")
    return {"detail": "Role deleted successfully"}