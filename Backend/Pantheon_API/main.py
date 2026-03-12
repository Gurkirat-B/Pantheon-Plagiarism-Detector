#NECESSARY LIBRARIES:
#fastapi
#uvicorn[standard]
#psycopg[binary]
#boto3
#passlib[bcrypt]==1.7.4
#bcrypt==4.0.1
#python-jose[cryptography]
#python-multipart
#pydantic[email]

from fastapi import FastAPI
from routes_auth import router as auth_router
from routes_submissions import router as submissions_router
from routes_engine import router as engine_router
from routes_assignments import router as assignments_router
from routes_courses import router as courses_router

app = FastAPI(title="Pantheon API")

app.include_router(auth_router)
app.include_router(submissions_router)
app.include_router(engine_router)
app.include_router(assignments_router)
app.include_router(courses_router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}