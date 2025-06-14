from typing import Optional


def get_user_by_email():
    pass


def create_user():
    pass


def update_user_password(user_id: int, new_hashed_password: str):
    pass


def store_refresh_token(user_id: int) -> str:
    return ""


def get_user_id_from_refresh_token(refresh_token: str) -> Optional[int]:
    pass


def delete_refresh_token(refresh_token: str):
    pass


def get_user_email_by_id(user_id: int) -> Optional[str]:
    pass



