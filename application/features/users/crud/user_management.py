from fastapi import HTTPException
from application.database.mssql_connection import get_sql_db_connection
import pyodbc


def delete_user_db(user_id: int) -> dict:
    """
    Deletes a user by ID.

    :param user_id: ID of the user to delete
    :type user_id: int
    :return: A message confirming deletion
    :rtype: dict
    """
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM Users WHERE id = ?", (user_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found.")

            conn.commit()
            return {"message": "User deleted successfully.", "user_id": user_id}

    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")