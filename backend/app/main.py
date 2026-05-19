from fastapi import FastAPI

from app.routers import expeditions, sets

app = FastAPI()

app.include_router(sets.router)
app.include_router(expeditions.router)

@app.get("/")
def root():
    return {"message": "hello world"}