"""
Assignment export functionality - JSON and ZIP downloads
"""
from fastapi import HTTPException
import pyodbc
from application.database.mssql_connection import get_sql_db_connection
from application.database.nosql_connection import get_container
from datetime import datetime
from typing import List, Dict, Optional
import zipfile
import io
import csv

from application.features.versionHistory.crud import get_html_content_from_version_document, convert_html_to_word_bytes


def export_student_assignments_json(student_id: int, assignment_ids: Optional[List[int]] = None) -> dict:
    """
    Export all assignment data for a student in JSON format.
    Includes student info, class associations, and all assignment data with versions and ratings.

    Args:
        student_id: The student's internal ID
        assignment_ids: Optional list of assignment IDs to filter by

    Returns:
        Dictionary with student data, classes, and assignments
    """
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # 1. Get student info
            cursor.execute("""
                SELECT
                    s.id, s.user_id, s.reading_level, s.writing_level, s.group_type,
                    u.first_name, u.last_name, u.email, u.gt_email,
                    y.name AS year_name
                FROM Students s
                INNER JOIN Users u ON s.user_id = u.id
                LEFT JOIN Years y ON s.year_id = y.id
                WHERE s.id = ?
            """, (student_id,))

            student_row = cursor.fetchone()
            if not student_row:
                raise HTTPException(status_code=404, detail=f"Student with id {student_id} not found")

            student_columns = [column[0] for column in cursor.description]
            student_data = dict(zip(student_columns, student_row))

            # 2. Get class associations with learning goals
            cursor.execute("""
                SELECT
                    c.id AS class_id, c.name AS class_name, c.course_code, c.term, c.type,
                    sc.learning_goal
                FROM StudentClasses sc
                INNER JOIN Classes c ON sc.class_id = c.id
                WHERE sc.student_id = ?
            """, (student_id,))

            class_rows = cursor.fetchall()
            class_columns = [column[0] for column in cursor.description]
            classes_data = [dict(zip(class_columns, row)) for row in class_rows]

            # 3. Get assignments (optionally filtered)
            if assignment_ids:
                placeholders = ",".join("?" for _ in assignment_ids)
                assignments_query = f"""
                    SELECT
                        a.id AS assignment_id, a.title, a.content, a.html_content,
                        a.date_created, a.blob_url, a.source_format, a.assignment_type_id,
                        c.id AS class_id, c.name AS class_name, c.course_code,
                        at.type AS assignment_type
                    FROM Assignments a
                    LEFT JOIN Classes c ON a.class_id = c.id
                    LEFT JOIN AssignmentTypes at ON a.assignment_type_id = at.id
                    WHERE a.student_id = ? AND a.id IN ({placeholders})
                    ORDER BY a.date_created DESC
                """
                cursor.execute(assignments_query, (student_id, *assignment_ids))
            else:
                assignments_query = """
                    SELECT
                        a.id AS assignment_id, a.title, a.content, a.html_content,
                        a.date_created, a.blob_url, a.source_format, a.assignment_type_id,
                        c.id AS class_id, c.name AS class_name, c.course_code,
                        at.type AS assignment_type
                    FROM Assignments a
                    LEFT JOIN Classes c ON a.class_id = c.id
                    LEFT JOIN AssignmentTypes at ON a.assignment_type_id = at.id
                    WHERE a.student_id = ?
                    ORDER BY a.date_created DESC
                """
                cursor.execute(assignments_query, (student_id,))

            assignment_rows = cursor.fetchall()
            assignment_columns = [column[0] for column in cursor.description]
            assignments_data = []

            # 4. For each assignment, get versions from Cosmos
            container = get_container()

            for row in assignment_rows:
                assignment = dict(zip(assignment_columns, row))

                # Query Cosmos for all versions of this assignment
                assignment_id = assignment["assignment_id"]
                query = f"SELECT * FROM c WHERE c.assignment_id = {assignment_id} ORDER BY c.version_number"
                versions = list(container.query_items(query=query, enable_cross_partition_query=True))

                # Structure class_info
                class_info = None
                if assignment.get("class_id"):
                    class_info = {
                        "id": assignment["class_id"],
                        "name": assignment["class_name"],
                        "course_code": assignment["course_code"]
                    }

                # Build assignment export object
                assignment_export = {
                    "assignment_id": assignment["assignment_id"],
                    "title": assignment["title"],
                    "content": assignment["content"],
                    "html_content": assignment.get("html_content"),
                    "date_created": assignment["date_created"].isoformat() if assignment["date_created"] else None,
                    "blob_url": assignment.get("blob_url"),
                    "source_format": assignment.get("source_format"),
                    "assignment_type": assignment.get("assignment_type"),
                    "assignment_type_id": assignment.get("assignment_type_id"),
                    "class_info": class_info,
                    "versions": versions
                }

                assignments_data.append(assignment_export)

        # 5. Build final response
        from datetime import datetime as dt
        export_data = {
            "student": student_data,
            "classes": classes_data,
            "assignments": assignments_data,
            "export_metadata": {
                "exported_at": dt.utcnow().isoformat(),
                "total_assignments": len(assignments_data),
                "filtered_by_ids": assignment_ids if assignment_ids else None
            }
        }

        return export_data

    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")


def _format_student_info(student_data: dict) -> str:
    """Format student information as readable text"""
    lines = [
        "=" * 60,
        "STUDENT INFORMATION",
        "=" * 60,
        f"Name: {student_data.get('first_name', '')} {student_data.get('last_name', '')}",
        f"Student ID: {student_data.get('id', 'N/A')}",
        f"User ID: {student_data.get('user_id', 'N/A')}",
        f"Email: {student_data.get('email', 'N/A')}",
        f"GT Email: {student_data.get('gt_email', 'N/A')}",
        f"Year: {student_data.get('year_name', 'N/A')}",
        f"Reading Level: {student_data.get('reading_level', 'N/A')}",
        f"Writing Level: {student_data.get('writing_level', 'N/A')}",
        f"Group Type: {student_data.get('group_type', 'N/A')}",
        "=" * 60
    ]
    return "\n".join(lines)


def _format_classes_and_goals(classes_data: List[dict]) -> str:
    """Format class associations and learning goals as readable text"""
    lines = [
        "=" * 60,
        "CLASS ASSOCIATIONS & LEARNING GOALS",
        "=" * 60,
        ""
    ]

    if not classes_data:
        lines.append("No class associations found.")
    else:
        for i, cls in enumerate(classes_data, 1):
            lines.extend([
                f"Class {i}:",
                f"  Name: {cls.get('class_name', 'N/A')}",
                f"  Course Code: {cls.get('course_code', 'N/A')}",
                f"  Term: {cls.get('term', 'N/A')}",
                f"  Type: {cls.get('type', 'N/A')}",
                f"  Learning Goal: {cls.get('learning_goal', 'N/A')}",
                ""
            ])

    lines.append("=" * 60)
    return "\n".join(lines)


def _format_rating_data(rating_data: dict) -> str:
    """Format rating data as readable text"""
    if not rating_data:
        return "No rating data available.\n"

    lines = ["RATING DATA", "-" * 40, ""]

    def format_section(title: str, data: dict, indent: int = 0):
        result = []
        prefix = "  " * indent
        result.append(f"{prefix}{title}:")
        for key, value in data.items():
            if isinstance(value, dict):
                result.extend(format_section(key, value, indent + 1))
            elif isinstance(value, list):
                result.append(f"{prefix}  {key}: {', '.join(str(v) for v in value)}")
            else:
                result.append(f"{prefix}  {key}: {value}")
        return result

    for section_name, section_data in rating_data.items():
        if isinstance(section_data, dict):
            lines.extend(format_section(section_name, section_data))
            lines.append("")
        else:
            lines.append(f"{section_name}: {section_data}")

    return "\n".join(lines)


def _create_assignments_summary_csv(assignments_data: List[dict]) -> str:
    """Create CSV summary of all assignments"""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Assignment ID",
        "Title",
        "Class",
        "Assignment Type",
        "Date Created",
        "Number of Versions",
        "Finalized",
        "Rating Status"
    ])

    # Data rows
    for assignment in assignments_data:
        versions = assignment.get("versions", [])
        finalized = any(v.get("finalized") for v in versions)
        has_ratings = any(v.get("rating_data") for v in versions)

        rating_status = "Pending"
        if has_ratings:
            if finalized and any(v.get("finalized") and v.get("rating_data") for v in versions):
                rating_status = "Rated"
            else:
                rating_status = "Partially Rated"

        writer.writerow([
            assignment.get("assignment_id", ""),
            assignment.get("title", ""),
            assignment.get("class_info", {}).get("name", "N/A") if assignment.get("class_info") else "N/A",
            assignment.get("assignment_type", "N/A"),
            assignment.get("date_created", ""),
            len(versions),
            "Yes" if finalized else "No",
            rating_status
        ])

    return output.getvalue()


def export_student_assignments_download(student_id: int, assignment_ids: Optional[List[int]] = None) -> bytes:
    """
    Export all assignment data for a student as a user-friendly ZIP file.

    ZIP structure:
    - student_info.txt
    - classes_and_goals.txt
    - assignments_summary.csv
    - assignments/
        - assignment_{id}_{title}/
            - original_assignment.docx
            - version_{n}.docx (with metadata)
            - ratings.txt

    Args:
        student_id: The student's internal ID
        assignment_ids: Optional list of assignment IDs to filter by

    Returns:
        ZIP file as bytes
    """
    try:
        # Get JSON export data first
        export_data = export_student_assignments_json(student_id, assignment_ids)

        # Create ZIP in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 1. Add student_info.txt
            student_info_text = _format_student_info(export_data["student"])
            zip_file.writestr("student_info.txt", student_info_text)

            # 2. Add classes_and_goals.txt
            classes_text = _format_classes_and_goals(export_data["classes"])
            zip_file.writestr("classes_and_goals.txt", classes_text)

            # 3. Add assignments_summary.csv
            summary_csv = _create_assignments_summary_csv(export_data["assignments"])
            zip_file.writestr("assignments_summary.csv", summary_csv)

            # 4. Add individual assignment folders
            for assignment in export_data["assignments"]:
                assignment_id = assignment["assignment_id"]
                title = assignment["title"]
                # Sanitize title for folder name
                safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)[:50]
                folder_name = f"assignments/assignment_{assignment_id}_{safe_title}"

                # 4a. Add original assignment content as Word doc
                if assignment.get("html_content"):
                    original_word_bytes = convert_html_to_word_bytes(assignment["html_content"])
                    zip_file.writestr(f"{folder_name}/original_assignment.docx", original_word_bytes)
                elif assignment.get("content"):
                    # If no HTML, create simple text doc
                    from docx import Document
                    doc = Document()
                    doc.add_heading(assignment["title"], 0)
                    doc.add_paragraph(assignment["content"])
                    doc_buffer = io.BytesIO()
                    doc.save(doc_buffer)
                    doc_buffer.seek(0)
                    zip_file.writestr(f"{folder_name}/original_assignment.docx", doc_buffer.getvalue())

                # 4b. Add each version as separate Word doc
                versions = assignment.get("versions", [])
                all_ratings = []

                for version in versions:
                    version_num = version.get("version_number", "unknown")
                    finalized_tag = "_finalized" if version.get("finalized") else ""

                    # Get HTML content from version
                    html_content = get_html_content_from_version_document(version)

                    # Add metadata header to version document
                    from docx import Document
                    doc = Document()
                    doc.add_heading(f"Version {version_num} Metadata", level=2)
                    metadata_lines = [
                        f"Version Number: {version_num}",
                        f"Modifier ID: {version.get('modifier_id', 'N/A')}",
                        f"Date Modified: {version.get('date_modified', 'N/A')}",
                        f"Finalized: {'Yes' if version.get('finalized') else 'No'}",
                        f"Has Rating: {'Yes' if version.get('rating_data') else 'No'}"
                    ]
                    for line in metadata_lines:
                        doc.add_paragraph(line)

                    doc.add_paragraph("_" * 60)
                    doc.add_heading("Content", level=2)

                    # Convert HTML content to Word and append
                    version_word_bytes = convert_html_to_word_bytes(html_content)

                    # Save with metadata
                    doc_buffer = io.BytesIO()
                    doc.save(doc_buffer)
                    doc_buffer.seek(0)

                    zip_file.writestr(
                        f"{folder_name}/version_{version_num}{finalized_tag}.docx",
                        version_word_bytes
                    )

                    # Collect ratings
                    if version.get("rating_data"):
                        all_ratings.append({
                            "version_number": version_num,
                            "finalized": version.get("finalized"),
                            "rating_data": version.get("rating_data")
                        })

                # 4c. Add ratings.txt if any ratings exist
                if all_ratings:
                    ratings_text = f"RATINGS FOR ASSIGNMENT {assignment_id}: {title}\n"
                    ratings_text += "=" * 60 + "\n\n"

                    for rating_info in all_ratings:
                        ratings_text += f"Version {rating_info['version_number']}"
                        if rating_info['finalized']:
                            ratings_text += " (FINALIZED)"
                        ratings_text += "\n" + "-" * 60 + "\n"
                        ratings_text += _format_rating_data(rating_info['rating_data'])
                        ratings_text += "\n\n"

                    zip_file.writestr(f"{folder_name}/ratings.txt", ratings_text)
                else:
                    zip_file.writestr(f"{folder_name}/ratings.txt", "No ratings available for this assignment.\n")

        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download export error: {str(e)}")
