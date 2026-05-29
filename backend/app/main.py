from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import expeditions, quickplay, sets

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://34.201.143.206:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sets.router)
app.include_router(expeditions.router)
app.include_router(quickplay.router)

@app.get("/")
def root():
    return {"message": "hello world"}