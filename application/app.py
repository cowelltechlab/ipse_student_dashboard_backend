from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# from application.core.config import get_settings

from application.features.students.routes import router as student_router
from application.features.classes.routes import router as classes_router
from application.features.studentProfile.routes import router as  profile_router
from application.features.versionHistory.routes import router as versions_router



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
application.include_router(profile_router, tags=["Profile"], prefix="/profile")
application.include_router(versions_router,  tags=["Assignment Versions"], prefix="/versions")



