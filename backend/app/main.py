from fastapi import FastAPI

from app.routers import sets

app = FastAPI()

app.include_router(sets.router)

@app.get("/")
def root():
    return {"message": "hello world"}