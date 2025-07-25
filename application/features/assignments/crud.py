from fastapi import HTTPException, status
import pyodbc
from application.database.mssql_connection import get_sql_db_connection
from application.database.nosql_connection import get_container
from application.database.mssql_crud_helpers import (
    create_many_records,
    create_record,
    fetch_all, 
    update_record,
)
from datetime import datetime
from typing import List, Dict

from application.features.assignments.schemas import AssignmentDetailResponse

TABLE_NAME = "Assignments"
def is_rating_meaningful(rating):
    if not rating:
        return False

    difficulty = rating.get("difficulty", "")
    best_changes = rating.get("best_changes", [])
    disliked_changes = rating.get("disliked_changes", [])
    return bool(difficulty.strip()) or bool(best_changes) or bool(disliked_changes)

def analyze_assignment_versions(assignment_id: str):
    container = get_container()

    query = f"SELECT * FROM c WHERE c.assignment_id = '{assignment_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))

    if not items:
        return {
            "finalized": False,
            "rating_status": "Pending",
            "date_modified": None
        }

    finalized = any(item.get("finalized") for item in items)
    date_modified = max(
        [datetime.fromisoformat(v["date_modified"]) for v in items if "date_modified" in v],
        default=None
    )

    # Find the finalized version, if any
    finalized_versions = [v for v in items if v.get("finalized")]
    finalized_version = finalized_versions[0] if finalized_versions else None

    # Check rating for finalized version
    if finalized_version and is_rating_meaningful(finalized_version.get("rating")):
        rating_status = "Rated"
    else:
        # Check any versions with meaningful rating
        if any(is_rating_meaningful(v.get("rating")) for v in items):
            rating_status = "Partially Rated"
        else:
            rating_status = "Pending"

    return {
        "finalized": finalized,
        "rating_status": rating_status,
        "date_modified": date_modified
    }


def get_all_assignment_versions_map():
    """
    Fetch all assignment versions from Cosmos DB and return a dict mapping assignment_id to its metadata.
    """
    container = get_container()

    query = "SELECT * FROM c"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))

    grouped = {}
    for item in items:
        aid = item.get("assignment_id")
        if not aid:
            continue
        grouped.setdefault(aid, []).append(item)

    result_map = {}

    for assignment_id, versions in grouped.items():
        finalized = any(v.get("finalized") for v in versions)
        date_modified = max(
            [datetime.fromisoformat(v["date_modified"]) for v in versions if "date_modified" in v],
            default=None
        )

        finalized_versions = [v for v in versions if v.get("finalized")]
        finalized_version = finalized_versions[0] if finalized_versions else None

        if finalized_version and is_rating_meaningful(finalized_version.get("rating")):
            rating_status = "Rated"
        elif any(is_rating_meaningful(v.get("rating")) for v in versions):
            rating_status = "Partially Rated"
        else:
            rating_status = "Pending"

        result_map[str(assignment_id)] = {
            "finalized": finalized,
            "rating_status": rating_status,
            "date_modified": date_modified
        }

    return result_map


''' 
*** GET ASSIGNMENTS ENDPOINT *** 
Fetch all assignments in Assignments table
'''
def get_all_assignments():
    """
    Fetch all assignments with student info and NoSQL-derived metadata (efficient version).
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT 
            a.id,
            a.student_id,
            a.title,
            a.class_id,
            a.date_created,
            a.blob_url,
            a.source_format,
            u.first_name,
            u.last_name
        FROM Assignments a
        INNER JOIN Students s ON a.student_id = s.id
        INNER JOIN Users u ON s.user_id = u.id
        """
        cursor.execute(query)
        records = cursor.fetchall()
        column_names = [column[0] for column in cursor.description]

        assignment_versions = get_all_assignment_versions_map()

        results = []
        for row in records:
            assignment = dict(zip(column_names, row))
            version_data = assignment_versions.get(str(assignment["id"]), {
                "finalized": False,
                "rating_status": "Pending",
                "date_modified": None
            })
            assignment.update(version_data)
            results.append(assignment)

        return results

    except pyodbc.Error as e:
        return {"error": str(e)}
    finally:
        conn.close()


def get_all_assignments_by_student_id(student_id):
    """
    Fetch all assignments with student info and NoSQL-derived metadata (efficient version).
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT 
            a.id,
            a.student_id,
            a.title,
            a.class_id,
            a.date_created,
            a.blob_url,
            a.source_format,
            u.first_name,
            u.last_name
        FROM Assignments a
        INNER JOIN Students s ON a.student_id = s.id
        INNER JOIN Users u ON s.user_id = u.id
        WHERE a.student_id = ?
        """
        cursor.execute(query, (student_id,))
        records = cursor.fetchall()
        column_names = [column[0] for column in cursor.description]

        assignment_versions = get_all_assignment_versions_map()

        results = []
        for row in records:
            assignment = dict(zip(column_names, row))
            version_data = assignment_versions.get(str(assignment["id"]), {
                "finalized": False,
                "rating_status": "Pending",
                "date_modified": None
            })
            assignment.update(version_data)
            results.append(assignment)

        return results

    except pyodbc.Error as e:
        return {"error": str(e)}
    finally:
        conn.close()


''' 
*** GET ASSIGNMENTS BY ID ENDPOINT *** 
Fetch assignments in Assignments table based on ID
'''
def get_assignments_by_id(assignment_id: int):
    """
    Fetch a single assignment and include student first/last name and NoSQL metadata.
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Fetch assignment from SQL
        query = """
        SELECT 
            a.id,
            a.student_id,
            a.title,
            a.class_id,
            a.content,
            a.date_created,
            a.blob_url,
            a.source_format,
            a.html_content,
            u.first_name,
            u.last_name
        FROM Assignments a
        INNER JOIN Students s ON a.student_id = s.id
        INNER JOIN Users u ON s.user_id = u.id
        WHERE a.id = ?
        """
        cursor.execute(query, (assignment_id,))
        record = cursor.fetchone()
        if not record:
            return None

        column_names = [column[0] for column in cursor.description]
        assignment_data = dict(zip(column_names, record))

        # 2. Fetch all versions from CosmosDB
        container = get_container()
        query = f"SELECT * FROM c WHERE c.assignment_id = '{assignment_id}'"
        versions = list(container.query_items(query=query, enable_cross_partition_query=True))

        if versions:
            # Sort by date_modified descending to get latest
            versions_sorted = sorted(
                versions,
                key=lambda v: v.get("date_modified", ""),
                reverse=True
            )

            assignment_data["date_modified"] = versions_sorted[0].get("date_modified")

            # Finalized check
            assignment_data["finalized"] = any(v.get("finalized") is True for v in versions)

            # Rating status
            ratings = [v.get("rating") for v in versions if v.get("rating")]
            final_version = next((v for v in versions if v.get("finalized")), None)

            if final_version and final_version.get("rating"):
                assignment_data["rating_status"] = "Rated"
            elif not ratings:
                assignment_data["rating_status"] = "Pending"
            else:
                assignment_data["rating_status"] = "Partially Rated"
        else:
            assignment_data["finalized"] = False
            assignment_data["rating_status"] = "Pending"
            assignment_data["date_modified"] = None

        return assignment_data

    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

''' 
*** POST ASSIGNMENT ENDPOINT *** 
Add a new Assignment in Assignments table
'''
def add_assignment(data):
    new_record = create_record(TABLE_NAME, data)

    if "error" in new_record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=new_record["error"]
        )
    
    return AssignmentDetailResponse(**new_record)

'''
*** POST ASSIGNMENT ENDPOINT *** 
Add many new assignments in Assignments table
'''
async def add_many_assignments(data) -> List[Dict]:
    new_records = create_many_records(TABLE_NAME, data)

    if new_records and isinstance(new_records, list) and "error" in new_records[0]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=new_records[0]["error"]
        )
    
    response = [AssignmentDetailResponse(**record) for record in new_records]
    return response

''' 
*** UPDATE ASSIGNMENT ENDPOINT *** 
Update existing assignment in Assignments table
'''
def update_assignment(assignment_id, data):
    return update_record(TABLE_NAME, assignment_id, data)

def get_all_assignment_types():
    """ 
    Fetch all types of assignments from AssigntmentTypes table 
    """
    return fetch_all(table_name="AssignmentTypes")