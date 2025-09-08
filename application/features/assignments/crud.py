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
from typing import List, Dict, Optional

from application.features.assignments.schemas import AssignmentCreateResponse, AssignmentDetailResponse
from application.features.users.crud.user_queries import get_users_with_roles

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
        [
            datetime.fromisoformat(v["date_modified"]).replace(tzinfo=None)
            for v in items
            if "date_modified" in v
        ],
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
        [
            datetime.fromisoformat(v["date_modified"]).replace(tzinfo=None)
            for v in versions
            if "date_modified" in v
        ],
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
def get_all_assignments(tutor_user_id: Optional[int] = None):
    """
    Fetch all assignments with student info and NoSQL-derived metadata (efficient version).
    """

    try:
        if tutor_user_id is not None:
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
            INNER JOIN TutorStudents ts ON ts.student_id = s.id
            WHERE ts.user_id = ?
            """
            params = (tutor_user_id,)

        else:
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

        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params if tutor_user_id is not None else ())
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


def get_all_assignments_by_student_id(student_id):
    """
    Fetch all assignments with student info and NoSQL-derived metadata (efficient version).
    """

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
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
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


def get_assignment_by_id(assignment_id: int):
    """
    Fetch a single assignment, including student/class info and NoSQL version metadata.
    Resolves modifier names and roles in a single query.
    """
    try:
        # 1. Fetch assignment from SQL
        query = """
        SELECT 
            a.id AS assignment_id,
            a.student_id AS student_id,
            a.title AS assignment_title,
            at.type AS assignment_type,
            a.assignment_type_id AS assignment_type_id,
            a.content AS assignment_content,
            a.date_created AS assignment_date_created,
            a.blob_url AS assignment_blob_url,
            a.source_format AS assignment_source_format,
            a.html_content AS assignment_html_content,

            -- Class info
            c.id AS class_id,
            c.name AS class_name,
            c.course_code AS class_course_code,

            -- Student info
            s.id AS student_internal_id,
            u.first_name AS student_first_name,
            u.last_name AS student_last_name

        FROM Assignments a
        INNER JOIN Students s ON a.student_id = s.id
        INNER JOIN Users u ON s.user_id = u.id
        LEFT JOIN AssignmentTypes at ON at.id = a.assignment_type_id
        LEFT JOIN Classes c ON c.id = a.class_id 
        WHERE a.id = ?
        """
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (assignment_id,))
            record = cursor.fetchone()
            if not record:
                return None

            column_names = [column[0] for column in cursor.description]
            assignment_data = dict(zip(column_names, record))

        # 2. Fetch versions from CosmosDB
        container = get_container()
        query = f"SELECT * FROM c WHERE c.assignment_id = {assignment_id}"
        versions = list(container.query_items(query=query, enable_cross_partition_query=True))

        assignment_data["versions"] = []

        if versions:
            versions_sorted = sorted(
                versions,
                key=lambda v: v.get("date_modified", ""),
                reverse=True
            )

            # Extract all modifier_ids to batch query user info
            modifier_ids = list({v.get("modifier_id") for v in versions_sorted if v.get("modifier_id")})
            modifier_info_map = get_users_with_roles(modifier_ids)

            # Overall metadata
            assignment_data["finalized"] = any(v.get("finalized") for v in versions)
            assignment_data["date_modified"] = versions_sorted[0].get("date_modified")

            ratings = [v.get("rating") for v in versions if v.get("rating")]
            final_version = next((v for v in versions if v.get("finalized")), None)
            if final_version and final_version.get("rating"):
                assignment_data["rating_status"] = "Rated"
            elif not ratings:
                assignment_data["rating_status"] = "Pending"
            else:
                assignment_data["rating_status"] = "Partially Rated"

            # Populate version details
            for v in versions_sorted:
                modifier_id = v.get("modifier_id")
                modifier_info = modifier_info_map.get(modifier_id) if modifier_id else None

                assignment_data["versions"].append({
                    "document_id": v.get("id"),
                    "version_number": v.get("version_number"),
                    "modified_by": modifier_info["name"] if modifier_info else None,
                    "modifier_role": modifier_info["role"] if modifier_info else None,
                    "date_modified": v.get("date_modified"),
                    "document_url": f"/cosmos/download/{v.get('id')}",
                    "finalized": v.get("finalized", False),
                    "rating_status": "Rated" if v.get("rating") else "Pending"
                })
        else:
            assignment_data["finalized"] = False
            assignment_data["rating_status"] = "Pending"
            assignment_data["date_modified"] = None

        return assignment_data

    except Exception as e:
        return {"error": str(e)}


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

    response = [AssignmentCreateResponse(**record) for record in new_records]
    return response


def update_assignment(assignment_id, data):
    """
    Update existing assignment in Assignments table
    """
    return update_record(TABLE_NAME, assignment_id, data)

def get_all_assignment_types():
    """ 
    Fetch all types of assignments from AssigntmentTypes table 
    """
    return fetch_all(table_name="AssignmentTypes")