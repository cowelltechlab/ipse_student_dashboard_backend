from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# from application.core.config import get_settings

from application.features.students.routes import router as student_router
from application.features.classes.routes import router as classes_router
from application.features.studentClasses.routes import router as student_classes_router
from application.features.assignments.routes import router as assignments_router

application = FastAPI()

origins = ["*"]

application.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


application.include_router(student_router, tags=["Students"], prefix="/students")
application.include_router(classes_router, tags=["Classes"], prefix="/classes")
application.include_router(student_classes_router, tags=["StudentClasses"], prefix="") 
application.include_router(assignments_router, tags=["Assignments"], prefix="/assignments") 
