from fastapi import FastAPI

from app.routers import expeditions, quickplay, sets

app = FastAPI()

app.include_router(sets.router)
app.include_router(expeditions.router)
app.include_router(quickplay.router)

@app.get("/")
def root():
    return {"message": "hello world"}