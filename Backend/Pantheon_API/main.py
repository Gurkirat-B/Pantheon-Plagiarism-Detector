#NECESSARY LIBRARIES:
#fastapi
#uvicorn[standard]
#psycopg[binary]
#boto3
#passlib[bcrypt]
#python-jose[cryptography]
#python-multipart

from fastapi import FastAPI
from routes_auth import router as auth_router
from routes_submissions import router as submissions_router

app = FastAPI(title="Pantheon API")

app.include_router(auth_router)
app.include_router(submissions_router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}