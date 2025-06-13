import jwt
import datetime
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from config import CONFIG


# Utility for handling OAuth bearer tokens. Accessed through /token endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def create_jwt_token(data: dict, expires_delta: int = 60) -> str:
    """
    Generate a JSON Web Token (JWT)

    :param data: Dictionary containing payload in JWT. Ex: {"user_id": "1", "role": "student"}
    :type data: dict
    :param expires_delta: time span in minutes for token to expire. Defaults to 60 (1hr)
    :type expires_delta: int
    :return: encoded JWT token
    :rtype: str
    """
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_delta)
    data.update({"exp": expire})

    # TODO: look into generating a secret key
    return jwt.encode(data, CONFIG["JWT_SECRET_KEY"], algorithm="HS256")


def verify_jwt_token(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Decodes and verifies JSON Web Token (JWT).

    :param token: encoded JWT
    :type token: str
    :returns: decoded JWT payload
    :rtype: dict
    :raises HTTPException: 401 error if token is expired or invalid
    """
    try:
        payload = jwt.decode(token, CONFIG["JWT_SECRET_KEY"], algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")