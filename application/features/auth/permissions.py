from fastapi import Depends, HTTPException
from auth.jwt_handler import verify_jwt_token
from typing import Callable

# TODO: bring back required access per role

def require_access(app_name: str, role_name: str) -> Callable[[dict], dict]:
    """
    Confirms users' access to an app based on their role and app name. This is 
    implemented as a FastAPI dependency that will be called by FastAPI. Role 
    examples include student, teacher, and admin.

    TODO: check if role exists in role table. Then check if user has that role

    :param app_name: name of app to be accessed
    :type app_name: str
    :param role_name: name of user's role
    :type role_name: str
    :returns: A function that acts as a FastAPI dependency. This function takes
              in user data (dict) and returns it (dict) if authorization is 
              successful.
    :rtype: Callable[[Dict], Dict]
    :raises HTTPException: 403 Forbidden if the user does not have access to 
                           the app or the appropriate role for it.
    """
    def dependency(user_data: dict = Depends(verify_jwt_token)):
        if app_name not in user_data["apps"]:
            raise HTTPException(
                status_code=403, detail=f"Access denied to app: {app_name}"
            )
        
        if role_name not in user_data["apps"][app_name]["roles"]:
            raise HTTPException(
                status_code=403, detail=f"{role_name} role required for {app_name}"
            )
        
        return user_data
    
    return dependency