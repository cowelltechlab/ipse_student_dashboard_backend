from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from application.features.students.routes import router as student_router
from application.features.classes.routes import router as classes_router
from application.features.student_profile.routes import router as profile_router
from application.features.assignment_version_generation.routes import router as assignment_version_generation
from application.features.versionHistory.routes import router as versions_router
from application.features.auth.router import router as auth_router
from application.features.roles.routes import router as roles_router
from application.features.studentClasses.routes import router as student_classes_router
from application.features.users.routes import router as users_router
from application.features.assignments.routes import router as assignments_router
from application.features.tutor_students.routes import router as tutor_students_router
from application.features.blob.routes import router as blob_router
from application.features.gpt.routes import router as gpt_router
from application.features.ratings.routes import router as ratings_router
from application.features.student_groups.routes import router as student_groups_router
from application.features.admin.routes import router as admin_router

application = FastAPI()

origins = ["*"]

application.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

application.include_router(auth_router, tags=["Auth"], prefix="/auth")
application.include_router(student_router, tags=["Students"], prefix="/students")
application.include_router(student_groups_router, tags=["Student Groups"], prefix="/student-groups")
application.include_router(classes_router, tags=["Classes"], prefix="/classes")
application.include_router(profile_router, tags=["Profile"], prefix="/profile")
application.include_router(assignment_version_generation, tags=["Assignment Version Generation"])
application.include_router(ratings_router, tags=["Ratings"], prefix="/rating-and-feedback")
application.include_router(versions_router, tags=["Assignment Versions"], prefix="/versions")
application.include_router(roles_router, tags=["Roles"], prefix="/roles")
application.include_router(student_classes_router, tags=["StudentClasses"], prefix="")
application.include_router(users_router, tags=["Users"], prefix="/users")
application.include_router(assignments_router, tags=["Assignments"], prefix="/assignments")
application.include_router(tutor_students_router, tags=["TutorStudents"], prefix="/tutor-students")
application.include_router(blob_router, tags=["Blob"], prefix="/blob")
application.include_router(gpt_router, prefix="/gpt", tags=["GPT"])
application.include_router(admin_router)  
