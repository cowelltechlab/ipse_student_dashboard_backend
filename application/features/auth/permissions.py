from fastapi import Depends, HTTPException
from application.features.auth.jwt_handler import verify_jwt_token
from typing import Callable

# TODO: bring back required access per role

def require_user_access() -> Callable[[dict], dict]:
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
        return {}
    
    return dependency


def require_teacher_access():
    pass

def require_admin_access():
    pass