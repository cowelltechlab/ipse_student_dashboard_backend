from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from application.core.config import get_settings



application = FastAPI()

origins = ["*"]

application.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@application.on_event("startup")
def preload_secrets():
    get_settings()  # Triggers one-time secret loading

application.include_router(auth_router, tags=["Auth"])
