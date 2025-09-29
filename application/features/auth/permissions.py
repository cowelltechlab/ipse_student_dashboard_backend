from fastapi import Depends, HTTPException, status
from application.features.auth.jwt_handler import verify_jwt_token
from typing import Dict, Optional, Set, List

ROLE_HIERARCHY = {
    "Admin": {"Admin", "Advisor", "Peer Tutor", "Student"},
    "Advisor": {"Advisor", "Peer Tutor", "Student"},
    "Peer Tutor": {"Peer Tutor", "Student"},
    "Student": {"Student"},
}

def _expand_roles(user_roles: Set[str]) -> Set[str]:
    expanded_roles = set()
    for role in user_roles:
        expanded_roles.update(ROLE_HIERARCHY.get(role, {role}))
    return expanded_roles

def _check_user_roles(user_data: dict, required_roles: Optional[List[str]] = None):
    if "role_names" not in user_data or not isinstance(user_data["role_names"], list):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role information missing from token."
        )

    user_roles = set(user_data["role_names"])
    expanded_user_roles = _expand_roles(user_roles)

    if not required_roles:
        if not expanded_user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authenticated user has no assigned roles in token."
            )
        return

    if not set(required_roles).intersection(expanded_user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Access Denied. Required roles: {required_roles}. "
                f"Your roles (expanded): {expanded_user_roles}"
            )
        )

def require_user_access(user_data: Dict = Depends(verify_jwt_token)) -> Dict:
    _check_user_roles(user_data)
    return user_data

def require_admin_only_access(user_data: Dict = Depends(verify_jwt_token)) -> Dict:
    """
    Confirms users' RBAC access as an *Admin only*.
    """
    _check_user_roles(user_data, required_roles=["Admin"])
    return user_data

def require_teacher_access(user_data: Dict = Depends(verify_jwt_token)):
    _check_user_roles(user_data, required_roles=["Advisor"])
    return user_data

def require_admin_access(user_data: Dict = Depends(verify_jwt_token)):
    _check_user_roles(user_data, required_roles=["Admin"])
    return user_data

def require_peer_tutor_access(user_data: Dict = Depends(verify_jwt_token)):
    _check_user_roles(user_data, required_roles=["Peer Tutor"])
    return user_data