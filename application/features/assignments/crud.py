from application.database.mssql_crud_helpers import (
    create_record, 
    fetch_by_id, 
    update_record,
    fetch_all
)

TABLE_NAME = "Assignments"

''' 
*** GET ASSIGNMENTS ENDPOINT *** 
Fetch all assignments in Assignments table
'''
def get_all_assignments():
    return fetch_all(TABLE_NAME)

''' 
*** GET ASSIGNMENTS BY ID ENDPOINT *** 
Fetch assignments in Assignments table based on ID
'''
def get_assignments_by_id(assignment_id):
    return fetch_by_id(TABLE_NAME, assignment_id)

''' 
*** POST ASSIGNMENT ENDPOINT *** 
Add a new Assignment in Assignments table
'''
def add_assignment(data):
    return create_record(TABLE_NAME, data)

''' 
*** UPDATE ASSIGNMENT ENDPOINT *** 
Update existing assignment in Assignments table
'''
def update_assignment(assignment_id, data):
    return update_record(TABLE_NAME, assignment_id, data)