from typing import Dict
from application.features.auth.jwt_handler import create_jwt_token
from application.features.auth.crud import store_refresh_token
from application.features.auth.schemas import TokenResponse
from application.features.users.crud.user_queries import get_user_with_roles_by_id


def create_token_response(user_id: int, expires_delta: int = 1500) -> TokenResponse:
    """
    Creates a complete token response with access token and refresh token
    for a given user ID.
    """
    user = get_user_with_roles_by_id(user_id)
    
    first_name = user.get("first_name")
    last_name = user.get("last_name")
    email = user.get("email")
    school_email = user.get("school_email")
    
    role_ids = user.get("role_ids", [])
    role_names = user.get("roles", [])
    
    profile_picture_url = user.get("profile_picture_url")
    student_id = user.get("student_id")
    
    access_token = create_jwt_token(
        {
            "user_id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "student_id": student_id,
            "email": email,
            "school_email": school_email,
            "role_ids": role_ids,
            "role_names": role_names,
            "profile_picture_url": profile_picture_url
        },
        expires_delta=expires_delta
    )
    
    refresh_token = store_refresh_token(user_id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


def create_token_response_with_saml_data(user_id: int, user_attributes: Dict, expires_delta: int = 1500) -> TokenResponse:
    """
    Creates a complete token response for SAML authentication, combining
    user attributes from SAML with database user data.
    """
    user = get_user_with_roles_by_id(user_id)
    
    first_name = user_attributes.get("first_name") or user.get("first_name")
    last_name = user_attributes.get("last_name") or user.get("last_name")
    email = user.get("email")
    school_email = user_attributes.get("school_email") or user.get("gt_email")
    
    role_ids = user.get("role_ids", [])
    role_names = user.get("roles", [])
    
    profile_picture_url = user.get("profile_picture_url")
    student_id = user.get("student_id")
    
    access_token = create_jwt_token(
        {
            "user_id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "student_id": student_id,
            "email": email,
            "school_email": school_email,
            "role_ids": role_ids,
            "role_names": role_names,
            "profile_picture_url": profile_picture_url,
        },
        expires_delta=expires_delta,
    )
    
    refresh_token = store_refresh_token(user_id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )