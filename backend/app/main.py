from fastapi import FastAPI

from app.routers import sets
from app.routers import randomize

app = FastAPI()

app.include_router(sets.router)
app.include_router(randomize.router)

@app.get("/")
def root():
    return {"message": "hello world"}