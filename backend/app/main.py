from fastapi import FastAPI

from app.routers import sets
from app.routers import randomize
from app.routers import expeditions

app = FastAPI()

app.include_router(sets.router)
app.include_router(randomize.router)
app.include_router(expeditions.router)

@app.get("/")
def root():
    return {"message": "hello world"}