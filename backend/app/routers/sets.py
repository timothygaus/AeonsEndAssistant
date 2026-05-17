from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import Set

router = APIRouter()

@router.get("/sets")
def get_sets(session: Session = Depends(get_session)):
    sets = session.exec(select(Set)).all()
    return sets