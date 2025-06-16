from fastapi import APIRouter, HTTPException, status
from typing import List
from application.features.studentClasses.crud import add_student_to_class, get_classes_for_student, remove_student_from_class
from application.features.studentClasses.schema import StudentClassAssociation, StudentClassOut

router = APIRouter()

@router.get("/students/{student_id}/classes", response_model=List[StudentClassOut])
def get_student_classes(student_id: int):
    classes = get_classes_for_student(student_id)
    if not classes:
        print(f"Student or classes not found")
    return classes

@router.post("/students/{student_id}/classes", status_code=201)
def assign_student_to_class(student_id: int, association: StudentClassAssociation):
    print(f"Assigning student {student_id} to class {association.class_id} with goal {association.learning_goal}")
    try:
        add_student_to_class(student_id, association)
        return {"message": "Class successfully assigned to student."}
    except Exception as e:
        print(f"Error assigning class: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/students/{student_id}/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student_class_association(student_id: int, class_id: int):
    try:
        remove_student_from_class(student_id, class_id)
    except Exception as e:
        # You can differentiate exceptions by error message if needed
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail="Could not delete association")
    return None