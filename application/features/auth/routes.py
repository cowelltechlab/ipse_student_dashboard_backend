"""
Sources:
- https://developers.google.com/identity/oauth2/web/guides/how-user-authz-works
- https://medium.com/@vivekpemawat/enabling-googleauth-for-fast-api-1c39415075ea
- Google Gemini
"""
from fastapi import HTTPException, APIRouter, Depends, Response, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from application.features import auth
from application.features.auth.google_oauth import *
from application.features.auth.jwt_handler import create_jwt_token
from application.features.auth.gatech_saml import (
    init_saml_auth,
    extract_user_attributes, 
    validate_saml_response,
    get_sso_url
)
from application.features.auth.crud import (
    get_user_email_by_id, 
    get_refresh_token_details,
    get_user_profile_picture_url, 
    get_user_role_names, 
    get_user_by_email,
    store_refresh_token,
    delete_refresh_token,
)
from typing import Dict
from application.features.auth.auth_helpers import (
    validate_user_email_login
)
from datetime import datetime
from application.features.auth.schemas import (
    UserLogin, 
    TokenResponse, 
    UserResponse
)
from application.features.auth.permissions import (
    require_user_access
)
from application.features.students.crud import get_student_by_user_id
from application.features.users.crud import get_user_with_roles_by_id



# This should include a way to log in through Google and generic username/password
''' 
Prepend all student routes with /students and collect all student-relevant 
endpoints under Students tag in SwaggerUI
'''
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router.post("/login/email")
async def email_login(user_credentials: UserLogin) -> TokenResponse:
    """
    Log user in via email and password without SSO.
    """
    user_id = -1

    try:
        user_id = validate_user_email_login(
            user_credentials.email, 
            user_credentials.password
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error during email login: {e}")
        raise HTTPException(
            status_code=500, 
            detail="An internal server error occurred."
        )

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
        expires_delta=1500
    )

    # Generate refresh token
    refresh_token = store_refresh_token(user_id) 

    return TokenResponse( 
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.get("/login/google")
async def google_login():
    """
    Retrieve Google SSO OAuth URL. Use to log user in with Google account.
    """
    backend_callback_uri = CONFIG["redirect_uris"][0]
    return { "google_auth_url": get_google_oauth_url(backend_callback_uri) }


@router.post("/logout")
async def logout(
    refresh_token: str, 
    user_data: Dict = Depends(require_user_access)
) -> Dict[str, str]:
    """
    Logs user out of app by deleting refresh token from DB.
    """
    delete_refresh_token(refresh_token)
    return {"message": "Log-out successful."}


@router.post("/refresh_token")
async def refresh_access_token(refresh_token: str) -> TokenResponse:
    """
    Retrieves current refresh token and generates a new access token (JWT) with
    new expiration date.
    """
    token_details = get_refresh_token_details(refresh_token)
    if not token_details:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")

    user_id = token_details["user_id"]
    expires_at = token_details["expires_at"]

    if expires_at < datetime.now():
        delete_refresh_token(refresh_token)
        raise HTTPException(
            status_code=401, 
            detail="Invalid or expired refresh token. Please log in again."
            )
    
    user = get_user_with_roles_by_id(user_id)

    first_name = user.get("first_name")
    last_name = user.get("last_name")
    email = user.get("email")
    school_email = user.get("school_email")

    role_ids = user.get("role_ids", [])
    role_names = user.get("roles", [])

    profile_picture_url = user.get("profile_picture_url")
    student_id = user.get("student_id")

    new_access_token = create_jwt_token(
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
    )   

    new_refresh_token = store_refresh_token(user_id)
    delete_refresh_token(refresh_token)

    return TokenResponse( 
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.get("/google/callback") # TODO: This URI must be registered in Google Cloud Console
async def google_auth_callback(code: str) -> TokenResponse: 
    """
    Handles callback from Google OAuth that redirects back to current app. 
    TODO: add in 400 status error for bad request, such as reusing old one-time token
    """
    backend_callback_uri = CONFIG["redirect_uris"][0]

    try:
        token_response_json = await exchange_code_for_token(
            code, backend_callback_uri)
        
        user_info = get_google_user_info(token_response_json["access_token"])

        email = user_info.get("email")

        if not email:
            raise HTTPException(
                status_code=403, 
                detail="No email passed back. Error from Google servers."
            )
        
        user = get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=403, 
                detail="User does not exist in system."
            )

        
        user_id = user["id"]
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
            expires_delta=1500
        )
            
        refresh_token = store_refresh_token(user_id)

        return TokenResponse( 
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )
    except ValueError as ve:
        print(f"Google ID token verification failed: {ve}")
        raise HTTPException(
            status_code=401, 
            detail="Invalid Google ID token. Please try logging in again."
        )


@router.get("/login/gatech")
async def gatech_sso_login(request: Request):
    auth = init_saml_auth(request)
    # optional return_to: where your app should go after successful ACS handling
    url = auth.login()  # signs AuthnRequest because of settings + keys
    return RedirectResponse(url, status_code=302)



@router.post("/gatech/saml2/acs")
async def gatech_saml_callback(
    request: Request,
    SAMLResponse: str = Form(...)
) -> TokenResponse:
    """
    Handle Georgia Tech SAML assertion consumer service callback.
    Processes the SAML response and creates user session.
    """
    try:
        # Initialize SAML auth with the POST data
        auth = init_saml_auth(request, post_data={"SAMLResponse": SAMLResponse})
        auth.process_response()
        
        # Process the SAML response
        auth.process_response()
        
        # Validate the SAML response
        validate_saml_response(auth)
        
        # Extract user attributes from SAML assertion
        user_attributes = extract_user_attributes(auth)
        
        # Check if user exists in our system
        email = user_attributes["email"]
        user = get_user_by_email(email)
        
        if not user:
            raise HTTPException(
                status_code=403,
                detail="User does not exist in system. Please contact administrator."
            )
        
        user_id = user["id"]
        user = get_user_with_roles_by_id(user_id)
        
        # Use existing user data, but update with GT attributes if needed
        first_name = user_attributes.get("first_name") or user.get("first_name")
        last_name = user_attributes.get("last_name") or user.get("last_name")
        email = user.get("email")
        school_email = user_attributes.get("school_email") or user.get("gt_email")
        
        role_ids = user.get("role_ids", [])
        role_names = user.get("roles", [])
        profile_picture_url = user.get("profile_picture_url")
        student_id = user.get("student_id")
        
        # Create JWT token
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
            expires_delta=1500
        )
        
        # Generate refresh token
        refresh_token = store_refresh_token(user_id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Georgia Tech SAML callback failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Georgia Tech SSO authentication failed."
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_data: Dict = Depends(require_user_access)
) -> UserResponse:
    """
    Retrieve identifying and access data for current user. 
    """
    email = user_data.get("email")
    id = user_data.get("user_id")
    roles = user_data.get("roles")
    profile_picture_url = user_data.get("profile_picture_url")

    if not email or not id or not roles:
        raise HTTPException(
            status_code=401, 
            detail="Invalid token payload: missing email, user_id, or roles."
        )
    
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=404, 
            detail="User found in token but not in database"
        )

    return UserResponse(
        id=id,
        email=email,
        roles=roles,
        first_name=user["first_name"],
        last_name=user["last_name"],
        school_email=email,
        profile_picture_url=profile_picture_url
    )



@router.get("/gatech/saml2/metadata")
async def metadata_xtml():
    """
    Returns SSO metadata file
    """
    with open("saml_metadata.xml", "r", encoding="utf-8") as f:
        metadata = f.read()

    return Response(content=metadata, media_type="application/xml")