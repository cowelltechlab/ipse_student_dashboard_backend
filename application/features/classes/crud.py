from application.database.mssql_connection import get_sql_db_connection
from application.database.mssql_crud_helpers import (
    create_record, 
    delete_record, 
    fetch_by_id, 
    update_record,
    fetch_all
)

TABLE_NAME = "Classes"

''' 
*** GET CLASSES ENDPOINT *** 
Fetch all classes in Classes table
'''
def get_all_classes():
    return fetch_all(TABLE_NAME)

''' 
*** GET CLASSES BY ID ENDPOINT *** 
Fetch class in Classes table based on ID
'''
def get_class_by_id(class_id):
    return fetch_by_id(TABLE_NAME, class_id)

''' 
*** POST CLASS ENDPOINT *** 
Add a new Class in Classes table
'''
def add_class(data):
    return create_record(TABLE_NAME, data)

''' 
*** UPDATE CLASS ENDPOINT *** 
Update existing Class in Classes table
'''
def update_class(class_id, data):
    return update_record(TABLE_NAME, class_id, data)

''' 
*** DELETE CLASS ENDPOINT *** 
Delete a Class
'''
def delete_class(class_id):
    return delete_record(TABLE_NAME, class_id)