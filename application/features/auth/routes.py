from fastapi import HTTPException, APIRouter, Depends, status, Query

# This should include a way to log in through Google and generic username/password
''' Prepend all student routes with /students and collect all student-relevant endpoints under Students tag in SwaggerUI'''
router = APIRouter()