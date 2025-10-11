"""
Assignment export routes - JSON and ZIP download operations
"""
from typing import Optional
from fastapi import Depends, HTTPException, APIRouter, Response, Query

from application.features.assignments.schemas import StudentAssignmentExportResponse
from application.features.assignments.crud import (
    export_student_assignments_json,
    export_student_assignments_download,
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
        - version documents
        - ratings.txt

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
