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

app = FastAPI(title="Pantheon API")

app.include_router(auth_router)
app.include_router(submissions_router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}