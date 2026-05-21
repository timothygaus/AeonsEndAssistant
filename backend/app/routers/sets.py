from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import delete, insert, select, Session

from app.database import get_session
from app.models import Set, UserSet

router = APIRouter()

@router.get('/sets')
def get_sets(session: Session = Depends(get_session)):
    sets = session.exec(select(Set)).all()
    return sets

@router.get('/sets/saved')
def get_user_sets(session: Session = Depends(get_session)):
    sets = session.exec(select(UserSet)).all()
    if not sets:
        return []
    return sets

@router.put('/sets/saved')
def add_user_set(user_sets: list[int], session: Session = Depends(get_session)):
    session.exec(delete(UserSet))
    for set_id in user_sets:
        session.add(UserSet(set_id=set_id))
    session.commit()