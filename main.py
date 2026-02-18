from fastapi import FastAPI
from requirements import router as requirement_router

app = FastAPI()

app.include_router(requirement_router)

@app.get("/")
def root():
    return {"message": "QMS Tool API running"}
