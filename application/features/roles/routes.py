
from fastapi import Depends, APIRouter, HTTPException, status

from application.features.auth.permissions import _expand_roles, require_admin_access, require_user_access

from application.database.mssql_crud_helpers import create_record, update_record, delete_record, fetch_by_id
from application.features.roles.crud import fetch_roles_by_names
from application.features.roles.schemas import RoleCreate, RoleResponse, RoleUpdate


router = APIRouter()

@router.get("/", response_model=list[RoleResponse])
async def get_roles(user_data: dict = Depends(require_user_access)):
    """
    Returns only the roles at and below the caller's role(s), based on ROLE_HIERARCHY.

    Admin   -> Admin, Advisor, Peer Tutor, Student
    Advisor -> Advisor, Peer Tutor, Student
    Tutor   -> Peer Tutor, Student
    Student -> Student
    """
    role_names = user_data.get("role_names")
    if not isinstance(role_names, list) or not role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role information missing from token."
        )

    allowed_roles = _expand_roles(set(role_names))
    return fetch_roles_by_names(allowed_roles)


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