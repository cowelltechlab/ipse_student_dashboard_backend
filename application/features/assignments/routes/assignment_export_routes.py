"""
Assignment export routes - JSON and ZIP download operations
"""
from typing import Optional
from fastapi import Depends, HTTPException, APIRouter, Response, Query

from application.features.assignments.schemas import StudentAssignmentExportResponse
from application.features.assignments.crud import (
    export_student_assignments_json,
    export_student_assignments_download,
    export_complete_student_data,
    export_all_students_complete_data,
)
from application.features.auth.permissions import require_user_access

router = APIRouter()


@router.get("/export/student/{student_id}/json", response_model=StudentAssignmentExportResponse)
def export_student_data_json(
    student_id: int,
    assignment_ids: Optional[str] = Query(None, description="Comma-separated list of assignment IDs to filter by"),
    _user = Depends(require_user_access)
):
    """
    Export all assignment data for a student in JSON format.
    Includes student info, class associations, assignments with all versions and ratings.

    Args:
        student_id: The student's internal ID
        assignment_ids: Optional comma-separated list of assignment IDs (e.g., "1,2,3")

    Returns:
        JSON with complete student assignment data
    """
    # Parse assignment_ids if provided
    parsed_assignment_ids = None
    if assignment_ids:
        try:
            parsed_assignment_ids = [int(aid.strip()) for aid in assignment_ids.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid assignment_ids format. Use comma-separated integers.")

    export_data = export_student_assignments_json(student_id, parsed_assignment_ids)

    # Return with attachment header
    from fastapi.responses import JSONResponse
    from datetime import datetime as dt, timezone

    filename = f"student_{student_id}_assignments_{dt.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"

    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\""
        }
    )


@router.get("/export/student/{student_id}/download")
def export_student_data_download(
    student_id: int,
    assignment_ids: Optional[str] = Query(None, description="Comma-separated list of assignment IDs to filter by"),
    _user = Depends(require_user_access)
):
    """
    Export all assignment data for a student as a user-friendly ZIP file.

    ZIP contains:
    - student_info.txt: Basic student information
    - classes_and_goals.txt: Class associations with learning goals
    - assignments_summary.csv: Spreadsheet of all assignments
    - assignments/ folder with individual assignment folders containing:
        - original_assignment.docx
        - version_{n}.docx: Generated content
        - version_{n}_complete_details.txt: All metadata (learning pathways, skills for success,
          student's ideas, selected options, generation history, rating history)
        - ratings.txt: Current ratings

    Args:
        student_id: The student's internal ID
        assignment_ids: Optional comma-separated list of assignment IDs (e.g., "1,2,3")

    Returns:
        ZIP file download
    """
    # Parse assignment_ids if provided
    parsed_assignment_ids = None
    if assignment_ids:
        try:
            parsed_assignment_ids = [int(aid.strip()) for aid in assignment_ids.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid assignment_ids format. Use comma-separated integers.")

    zip_bytes = export_student_assignments_download(student_id, parsed_assignment_ids)

    from datetime import datetime as dt, timezone
    filename = f"student_{student_id}_export_{dt.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\""
        }
    )


@router.get("/export/student/{student_id}/complete")
def export_complete_student_data_download(
    student_id: int,
    assignment_ids: Optional[str] = Query(None, description="Comma-separated list of assignment IDs to filter by"),
    _user = Depends(require_user_access)
):
    """
    Export COMPLETE student data combining profile and assignments in one comprehensive ZIP.

    This is the most comprehensive export available, including:
    - Complete student profile (strengths, challenges, goals, interests)
    - All classes with learning goals
    - PowerPoint achievements tracking
    - All assignments with original content
    - All assignment versions and regenerations
    - Learning pathways with full reasoning (generated options)
    - Skills for success for each version
    - Student's ideas for changes (additional edit suggestions)
    - All ratings and feedback history
    - Rating history for each version
    - Generation history for each version

    ZIP contains:
    - student_profile.txt: Complete detailed profile
    - student_profile.json: Profile in JSON format for programmatic access
    - classes_and_learning_goals.txt: Enrolled classes with goals
    - assignments_summary.csv: Spreadsheet overview of all assignments
    - assignments/ folder: Individual folders for each assignment
        - version_{n}_complete_details.txt: Complete metadata for each version
    - export_metadata.txt: Information about the export contents

    Args:
        student_id: The student's internal ID
        assignment_ids: Optional comma-separated list of assignment IDs to filter (e.g., "1,2,3")

    Returns:
        Comprehensive ZIP file with all student data
    """
    # Parse assignment_ids if provided
    parsed_assignment_ids = None
    if assignment_ids:
        try:
            parsed_assignment_ids = [int(aid.strip()) for aid in assignment_ids.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid assignment_ids format. Use comma-separated integers.")

    zip_bytes = export_complete_student_data(student_id, parsed_assignment_ids)

    from datetime import datetime as dt, timezone
    filename = f"student_{student_id}_complete_export_{dt.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\""
        }
    )


@router.get("/export/all-students/download")
def export_all_students_data_download(
    student_ids: Optional[str] = Query(None, description="Comma-separated list of student IDs to filter (exports ALL if omitted)"),
    assignment_ids: Optional[str] = Query(None, description="Comma-separated list of assignment IDs to filter by"),
    _user = Depends(require_user_access)
):
    """
    Export complete data for ALL students (or filtered subset) in one comprehensive ZIP file.

    This is the most comprehensive export available for multiple students, creating a master ZIP
    containing individual folders for each student with their complete data.

    ZIP structure:
    - export_summary.csv: Overview of all students (ID, name, email, year, assignment counts)
    - export_metadata.txt: Information about the export
    - student_{id}_{name}/ folders: Individual student data including:
        - Complete profile (txt and json)
        - Classes and learning goals
        - Assignments summary CSV
        - assignments/ folder with all assignment versions
        - Complete metadata for each version (learning pathways, skills, ratings, history)

    Each student folder contains the same comprehensive data as the individual student export:
    - Learning pathways with full reasoning (generated options)
    - Skills for success for each version
    - Student's ideas for changes (additional edit suggestions)
    - All ratings and feedback history
    - Rating history for each version
    - Generation history for each version

    WARNING: This export can be very large for many students. Consider filtering by student_ids
    if you only need specific students.

    Args:
        student_ids: Optional comma-separated list of student IDs (e.g., "251,252,253").
                    If omitted, exports ALL active students.
        assignment_ids: Optional comma-separated list of assignment IDs to filter by

    Returns:
        Master ZIP file with all student data
    """
    # Parse student_ids if provided
    parsed_student_ids = None
    if student_ids:
        try:
            parsed_student_ids = [int(sid.strip()) for sid in student_ids.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid student_ids format. Use comma-separated integers.")

    # Parse assignment_ids if provided
    parsed_assignment_ids = None
    if assignment_ids:
        try:
            parsed_assignment_ids = [int(aid.strip()) for aid in assignment_ids.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid assignment_ids format. Use comma-separated integers.")

    zip_bytes = export_all_students_complete_data(parsed_student_ids, parsed_assignment_ids)

    from datetime import datetime as dt, timezone
    filename = f"all_students_export_{dt.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\""
        }
    )
