# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import sqlalchemy.exc
from typing import List
from db.models import Portfolio, Profile, get_db
from api.schemas.user_data import PortfolioCreate, PortfolioResponse
from api.dependencies import get_current_user
import uuid

router = APIRouter(
    prefix="/api/v1/portfolio",
    tags=["Portfolio"],
)

def get_or_create_profile(db: Session, user_payload: dict):
    user_id_str = user_payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user_id = uuid.UUID(user_id_str)
    try:
        profile = db.query(Profile).filter(Profile.id == user_id).first()
        
        if not profile:
            profile = Profile(id=user_id, email=user_payload.get("email", ""))
            db.add(profile)
            db.commit()
            db.refresh(profile)
            
        return profile
    except sqlalchemy.exc.OperationalError as e:
        raise HTTPException(status_code=503, detail="Database is currently unreachable.") from e

@router.get("/", response_model=List[PortfolioResponse])
def get_portfolio(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_or_create_profile(db, user)
    try:
        items = db.query(Portfolio).filter(Portfolio.user_id == profile.id).all()
        return items
    except sqlalchemy.exc.OperationalError as e:
        raise HTTPException(status_code=503, detail="Database is currently unreachable.") from e

@router.post("/", response_model=PortfolioResponse)
def add_to_portfolio(item: PortfolioCreate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_or_create_profile(db, user)
        
    try:
        new_item = Portfolio(
            user_id=profile.id, 
            symbol=item.symbol,
            price=item.price,
            quantity=item.quantity,
            date_acquired=item.date_acquired
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        
        return new_item
    except sqlalchemy.exc.OperationalError as e:
        raise HTTPException(status_code=503, detail="Database is currently unreachable.") from e

@router.delete("/{item_id}")
def remove_from_portfolio(item_id: uuid.UUID, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_or_create_profile(db, user)
    try:
        item = db.query(Portfolio).filter(Portfolio.id == item_id, Portfolio.user_id == profile.id).first()
        
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
            
        db.delete(item)
        db.commit()
        return {"status": "success", "detail": "Item removed from portfolio"}
    except sqlalchemy.exc.OperationalError as e:
        raise HTTPException(status_code=503, detail="Database is currently unreachable.") from e
