from application.database.mssql_crud_helpers import (
    create_record, 
    delete_record, 
    fetch_all, 
    fetch_by_id, 
    update_record
)

TABLE_NAME = "Students"


def get_all_students():
    return fetch_all(TABLE_NAME)


def get_student_by_id(student_id):
    return fetch_by_id(TABLE_NAME, student_id)


def add_student(data):
    return create_record(TABLE_NAME, data)


def update_student(student_id, data):
    return update_record(TABLE_NAME, student_id, data)


def delete_student(student_id):
    return delete_record(TABLE_NAME, student_id)
