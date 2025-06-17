from passlib.context import CryptContext

from application.features.auth.db_crud import get_user_by_email

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


def authenticate_user_email_login(email: str, password: str):
    """
    TODO: implement
    """
    user = get_user_by_email(email)

    if not user:
        # TODO: raise exception
        return False

    hashed_password = hash_password(password)
    if not verify_password(password, hash_password) and \
        user["password_hash"] != hashed_password:
        # TODO: raise exception
        return False

    return True
