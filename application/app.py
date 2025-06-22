from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# from application.core.config import get_settings

from application.features.students.routes import router as student_router
from application.features.classes.routes import router as classes_router
from application.features.auth.routes import router as auth_router
from application.features.roles.routes import router as roles_router


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
application.include_router(classes_router, tags=["Classes"], prefix="/classes")
application.include_router(roles_router, tags=["Roles"], prefix="/roles")
