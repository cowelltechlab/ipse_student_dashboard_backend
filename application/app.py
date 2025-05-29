from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# from application.core.config import get_settings

from application.features.students.routes import router as student_router


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
