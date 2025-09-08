
import datetime
import pyodbc
from typing import List
from fastapi import HTTPException
from application.database.mssql_connection import get_sql_db_connection
from application.database.nosql_connection import get_cosmos_db_connection
from application.features.ratings.schemas import AssignmentRatingData, RatingUpdateRequest
from application.features.versionHistory.schemas import AssignmentVersionResponse
from application.features.assignment_version_generation.schemas import LearningPathwayOption
from application.features.student_profile.schemas import StudentProfileResponse, StudentClass, ProfileSummaries

# Database configuration
DATABASE_NAME = "ai-prompt-storage"
PROFILE_CONTAINER_NAME = "ai-student-profile"
VERSIONS_CONTAINER_NAME = "ai-assignment-versions-v2"

_cosmos = get_cosmos_db_connection()
_db = _cosmos.get_database_client(DATABASE_NAME)
versions_container = _db.get_container_client(VERSIONS_CONTAINER_NAME)
profile_container = _db.get_container_client(PROFILE_CONTAINER_NAME)


def get_rating_data_by_assignment_version_id(assignment_version_id: str) -> AssignmentRatingData:
    """
    Comprehensive data gathering for assignment rating endpoint.
    Fetches all necessary data from both Cosmos DB and SQL Server.
    """
    try:
        # 1. Get assignment version document from Cosmos DB
        try:
            version_doc = list(versions_container.query_items(
                query="SELECT * FROM c WHERE c.id = @id",
                parameters=[{"name": "@id", "value": assignment_version_id}],
                enable_cross_partition_query=True
            ))
            if not version_doc:
                raise HTTPException(status_code=404, detail="Assignment version not found")
            
            version_doc = version_doc[0]
            assignment_id = version_doc["assignment_id"]
            student_id = version_doc["student_id"]
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch assignment version: {str(e)}")

        # 2. Get SQL data - assignment, student, user, and class information
        try:
            with get_sql_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get assignment information
                cursor.execute("""
                    SELECT id, student_id, title, class_id, content, html_content, assignment_type_id
                    FROM dbo.Assignments 
                    WHERE id = ?
                """, (assignment_id,))
                assignment_row = cursor.fetchone()
                if not assignment_row:
                    raise HTTPException(status_code=404, detail="Assignment not found")
                
                assignment_info = {
                    "id": assignment_row[0],
                    "student_id": assignment_row[1],
                    "title": assignment_row[2],
                    "class_id": assignment_row[3],
                    "content": assignment_row[4],
                    "html_content": assignment_row[5],
                    "assignment_type_id": assignment_row[6]
                }
                
                # Get student information
                cursor.execute("""
                    SELECT id, user_id, year_id, reading_level, writing_level, 
                           active_status, ppt_embed_url, ppt_edit_url, group_type
                    FROM dbo.Students 
                    WHERE id = ?
                """, (student_id,))
                student_row = cursor.fetchone()
                if not student_row:
                    raise HTTPException(status_code=404, detail="Student not found")
                
                student_info = {
                    "id": student_row[0],
                    "user_id": student_row[1],
                    "year_id": student_row[2],
                    "reading_level": student_row[3],
                    "writing_level": student_row[4],
                    "active_status": student_row[5],
                    "ppt_embed_url": student_row[6],
                    "ppt_edit_url": student_row[7],
                    "group_type": student_row[8]
                }
                
                # Get user information
                cursor.execute("""
                    SELECT id, email, first_name, last_name, gt_email, 
                           profile_picture_url, is_active
                    FROM dbo.Users 
                    WHERE id = ?
                """, (student_info["user_id"],))
                user_row = cursor.fetchone()
                if not user_row:
                    raise HTTPException(status_code=404, detail="User not found")
                
                user_info = {
                    "id": user_row[0],
                    "email": user_row[1],
                    "first_name": user_row[2],
                    "last_name": user_row[3],
                    "gt_email": user_row[4],
                    "profile_picture_url": user_row[5],
                    "is_active": user_row[6]
                }
                
                # Get year name
                cursor.execute("""
                    SELECT name FROM dbo.Years WHERE id = ?
                """, (student_info["year_id"],))
                year_row = cursor.fetchone()
                year_name = year_row[0] if year_row else "Unknown"
                
                # Get class information and student classes
                cursor.execute("""
                    SELECT sc.class_id, sc.learning_goal, c.name, c.course_code, c.term, c.type
                    FROM dbo.StudentClasses sc
                    JOIN dbo.Classes c ON sc.class_id = c.id
                    WHERE sc.student_id = ?
                """, (student_id,))
                classes_rows = cursor.fetchall()
                
                classes = []
                for class_row in classes_rows:
                    classes.append(StudentClass(
                        class_id=class_row[0],
                        class_name=class_row[2],
                        course_code=class_row[3],
                        learning_goal=class_row[1]
                    ))
                
        except pyodbc.Error as e:
            raise HTTPException(status_code=500, detail=f"SQL Database error: {str(e)}")

        # 3. Get student profile from Cosmos DB
        try:
            profile_docs = list(profile_container.query_items(
                query="SELECT * FROM c WHERE c.student_id = @sid",
                parameters=[{"name": "@sid", "value": student_id}],
                enable_cross_partition_query=True
            ))
            if not profile_docs:
                raise HTTPException(status_code=404, detail="Student profile not found")
            
            profile_doc = profile_docs[0]
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch student profile: {str(e)}")

        # 4. Build the response data structures
        
        # Convert generated options to LearningPathwayOption objects
        generated_options = []
        for option in version_doc.get("generated_options", []):
            generated_options.append(LearningPathwayOption(
                name=option.get("name", ""),
                description=option.get("description", ""),
                why_good_existing=option.get("why_good_existing", ""),
                why_challenge=option.get("why_challenge", ""),
                why_good_growth=option.get("why_good_growth", ""),
                selection_logic=option.get("selection_logic", ""),
                internal_id=option.get("internal_id", "")
            ))
        
        # Build student profile response
        summaries = profile_doc.get("summaries", {})
        profile_summaries = ProfileSummaries(
            strengths_short=summaries.get("strength_short", ""),
            short_term_goals=summaries.get("short_term_goals", ""),
            long_term_goals=summaries.get("long_term_goals", ""),
            best_ways_to_help=summaries.get("best_ways_to_help", ""),
            vision=profile_doc.get("vision", "")
        )
        
        student_profile = StudentProfileResponse(
            student_id=student_id,
            user_id=student_info["user_id"],
            first_name=user_info["first_name"],
            last_name=user_info["last_name"],
            email=user_info["email"],
            gt_email=user_info["gt_email"],
            year_name=year_name,
            profile_picture_url=user_info["profile_picture_url"],
            ppt_embed_url=student_info["ppt_embed_url"],
            ppt_edit_url=student_info["ppt_edit_url"],
            classes=classes,
            strengths=profile_doc.get("strengths", []),
            challenges=profile_doc.get("challenges", []),
            long_term_goals=profile_doc.get("long_term_goals", ""),
            short_term_goals=profile_doc.get("short_term_goals", ""),
            best_ways_to_help=profile_doc.get("best_ways_to_help", []),
            hobbies_and_interests=profile_doc.get("hobbies_and_interests", ""),
            profile_summaries=profile_summaries
        )
        
        # Extract HTML content
        original_assignment_html = assignment_info.get("html_content", "") or assignment_info.get("content", "")
        
        # Get version HTML from final_generated_content
        final_content = version_doc.get("final_generated_content", {}).get("json_content", {})
        version_html_sections = []
        
        if final_content.get("assignmentInstructionsHtml"):
            version_html_sections.append(final_content["assignmentInstructionsHtml"])
        if final_content.get("stepByStepPlanHtml"):
            version_html_sections.append(final_content["stepByStepPlanHtml"])
        if final_content.get("promptsHtml"):
            version_html_sections.append(final_content["promptsHtml"])
        
        support_tools = final_content.get("supportTools", {})
        for tool_key in ["toolsHtml", "aiPromptingHtml", "aiPolicyHtml"]:
            if support_tools.get(tool_key):
                version_html_sections.append(support_tools[tool_key])
        
        if final_content.get("motivationalMessageHtml"):
            version_html_sections.append(final_content["motivationalMessageHtml"])
        
        version_html = "<hr>".join(version_html_sections)
        
        # Build and return the comprehensive rating data
        return AssignmentRatingData(
            assignment_version_id=assignment_version_id,
            assignment_id=str(assignment_id),
            assignment_name=assignment_info["title"],
            generated_options=generated_options,
            original_assignment_html=original_assignment_html,
            version_html=version_html,
            student_profile=student_profile
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error gathering rating data: {str(e)}")


def upsert_rating_fields(assignment_version_id: str, rating_data: RatingUpdateRequest) -> dict:
    """
    Store or update rating information in the assignment version Cosmos document.
    """
    try:
        # 1. Find the assignment version document
        version_docs = list(versions_container.query_items(
            query="SELECT * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": assignment_version_id}],
            enable_cross_partition_query=True
        ))
        
        if not version_docs:
            raise HTTPException(status_code=404, detail="Assignment version not found")
        
        existing_doc = version_docs[0]
        
        # 2. Convert rating data to dictionary, excluding unset values
        rating_dict = rating_data.dict(exclude_unset=True)
        
        # 3. Convert datetime to ISO format if present
        if "date_modified" in rating_dict and isinstance(rating_dict["date_modified"], datetime.datetime):
            rating_dict["date_modified"] = rating_dict["date_modified"].isoformat()
        
        # 4. Add or update the rating fields in the document
        if "rating_data" not in existing_doc:
            existing_doc["rating_data"] = {}
        
        # Update each section if provided
        for section_key, section_data in rating_dict.items():
            if section_key != "date_modified":
                existing_doc["rating_data"][section_key] = section_data
        
        # Always update the last modified timestamp
        existing_doc["rating_data"]["last_rating_update"] = rating_dict.get("date_modified", datetime.datetime.utcnow().isoformat())
        
        # 5. Save back to Cosmos DB
        versions_container.replace_item(item=existing_doc["id"], body=existing_doc)
        
        return {
            "success": True,
            "assignment_version_id": assignment_version_id,
            "rating_data": existing_doc["rating_data"],
            "message": "Rating data saved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save rating data: {str(e)}")


def update_rating_fields(
    container,
    assignment_id: str,
    version_number: int,
    modifier_id: str,
    update_data: RatingUpdateRequest
) -> AssignmentVersionResponse:
    # Find the existing version using all three filters

    print("Querying CosmosDB with:")
    print(f"assignment_id: {assignment_id} ({type(assignment_id)})")
    print(f"version_number: {version_number} ({type(version_number)})")
    print(f"modifier_id: {modifier_id} ({type(modifier_id)})")

    query = """
    SELECT * FROM c 
    WHERE c.assignment_id = @assignment_id 
      AND c.version_number = @version_number 
      AND c.modifier_id = @modifier_id
    """
    params = [
        {"name": "@assignment_id", "value": assignment_id},
        {"name": "@version_number", "value": version_number},
        {"name": "@modifier_id", "value": modifier_id}
    ]
    

    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

    if not items:
        raise HTTPException(status_code=404, detail="Version not found")
    
    print("Returned items:", items)


    existing = items[0]
    doc_id = existing["id"]
    partition_key = existing["modifier_id"]

    update_dict = update_data.dict(exclude_unset=True)

    # Optional: ISO format datetime
    if "date_modified" in update_dict and isinstance(update_dict["date_modified"], datetime):
        update_dict["date_modified"] = update_dict["date_modified"].isoformat()

    for key, value in update_dict.items():
        existing[key] = value

    try:
        container.replace_item(item=doc_id, body=existing)
        existing["modifier_id"] = int(existing["modifier_id"])
        return AssignmentVersionResponse(**existing)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update rating info: {str(e)}")

