from passlib.context import CryptContext
from fastapi import HTTPException

from application.features.auth.crud import get_user_by_email

pwd_context = CryptContext(schemes=["bcrypt"])

def verify_password(plain_password, hashed_password) -> bool:
    """
    Validate that plain password, when hashed, matches with the stored hashed 
    equivalent.

    :param plain_password: original, non-encoded user password
    :type plain_password: str
    :hashed_password: Possible encoded / hashed version of the plain password
    :type hashed_password: str
    :returns: True if passwords match, False otherwise
    :rtype: bool
    """
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """
    Converts plain password into a hashed (encoded) version.

    :param password: original password
    :type password: str
    :returns: hashed password
    :rtype: str
    """
    return pwd_context.hash(password)


def validate_user_email_login(email: str, password: str) -> int:
    """
    Check for email and password. The email must exist in the database and 
    have a matching hashed password with what is passed in.
    """
    user = get_user_by_email(email, True)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized. User not found."
        )
    
    print(user)
    if "password_hash" not in user or "id" not in user:
        raise HTTPException(
            status_code=400,
            detail="Bad Request. Database request did not return a password."
        )

    hashed_password = hash_password(password)
    if not verify_password(password, hashed_password) and \
        user["password_hash"] != hashed_password:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized. Incorrect email or password."
        )

    return user["id"]
