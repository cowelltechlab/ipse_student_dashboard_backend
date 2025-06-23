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
    """
    Expands a set of user roles to include all roles they implicitly have 
    access to via the ROLE_HIERARCHY.
    """
    expanded_roles = set()
    for role in user_roles:
        expanded_roles.update(ROLE_HIERARCHY.get(role, {role}))
    return expanded_roles



def _check_user_roles(user_data: dict, required_roles: Optional[List[str]] = None):
    """
    Helper function for checking that user roles from JWT match required roles.

    :param user_data: JWT data
    :type user_data: dict
    :param required_roles: list of access roles required for user to have
    :type required_roles: Optional[List[str]]
    :raises HTTPException: when JWT token lacks properly formatted roles, or 
                           user does not have required roles.
    """
    # Check that JWT includes roles and is appropriately formatted
    if "roles" not in user_data or not isinstance(user_data["roles"], list):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role information missing from token."
        )

    user_roles = set(user_data["roles"])
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
    """
    Confirms users' access application by having at least one role present in a
    valid JWT.

    :param user_data: User data stored in JSON Web Token (JWT)
    :type user_data: Dict
    :returns: User data in verified JWT token if access is approved.
    :rtype: Dict
    :raises HTTPException: 403 Forbidden if the user does not have the 
                           appropriate role for it, or JWT missing role data.
    """
    _check_user_roles(user_data)
    return user_data


def require_teacher_access(user_data: Dict = Depends(verify_jwt_token)):
    """
    Confirms users' RBAC access as an advisor / teacher user.

    :param user_data: User data stored in JSON Web Token (JWT)
    :type user_data: Dict
    :returns: User data in verified JWT token if access is approved.
    :rtype: Dict
    :raises HTTPException: 403 Forbidden if the user does not have the 
                           appropriate role for it, or JWT missing role data.
    """
    _check_user_roles(user_data, required_roles=["Advisor"])
    return user_data


def require_admin_access(user_data: Dict = Depends(verify_jwt_token)):
    """
    Confirms users' RBAC access as an admin user.

    :param user_data: User data stored in JSON Web Token (JWT)
    :type user_data: Dict
    :returns: User data in verified JWT token if access is approved.
    :rtype: Dict
    :raises HTTPException: 403 Forbidden if the user does not have the 
                           appropriate role for it, or JWT missing role data.
    """
    _check_user_roles(user_data, required_roles=["Admin"])
    return user_data


def require_peer_tutor_access(user_data: Dict = Depends(verify_jwt_token)):
    """
    Confirms users' RBAC access as a peer tutor user.

    :param user_data: User data stored in JSON Web Token (JWT)
    :type user_data: Dict
    :returns: User data in verified JWT token if access is approved.
    :rtype: Dict
    :raises HTTPException: 403 Forbidden if the user does not have the 
                           appropriate role for it, or JWT missing role data.
    """
    _check_user_roles(user_data, required_roles=["Peer Tutor"])
    return user_data