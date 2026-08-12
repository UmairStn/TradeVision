from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import sqlalchemy.exc
from typing import List
from db.models import Watchlist, Profile, get_db
from api.schemas.user_data import WatchlistCreate, WatchlistResponse
from api.dependencies import get_current_user
import uuid

router = APIRouter(
    prefix="/api/v1/watchlist",
    tags=["Watchlist"],
)

def get_or_create_profile(db: Session, user_payload: dict):
    user_id_str = user_payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user_id = uuid.UUID(user_id_str)
    try:
        profile = db.query(Profile).filter(Profile.id == user_id).first()
        
        if not profile:
            # Create profile automatically if it doesn't exist
            profile = Profile(id=user_id, email=user_payload.get("email", ""))
            db.add(profile)
            db.commit()
            db.refresh(profile)
            
        return profile
    except sqlalchemy.exc.OperationalError as e:
        raise HTTPException(status_code=503, detail="Database is currently unreachable.") from e

@router.get("/", response_model=List[WatchlistResponse])
def get_watchlist(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_or_create_profile(db, user)
    try:
        items = db.query(Watchlist).filter(Watchlist.user_id == profile.id).all()
        return items
    except sqlalchemy.exc.OperationalError as e:
        raise HTTPException(status_code=503, detail="Database is currently unreachable.") from e

@router.post("/", response_model=WatchlistResponse)
def add_to_watchlist(item: WatchlistCreate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_or_create_profile(db, user)
    
    try:
        # Check if already exists
        existing = db.query(Watchlist).filter(
            Watchlist.user_id == profile.id, 
            Watchlist.symbol == item.symbol
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Symbol already in watchlist")
            
        new_item = Watchlist(user_id=profile.id, symbol=item.symbol)
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        
        return new_item
    except sqlalchemy.exc.OperationalError as e:
        raise HTTPException(status_code=503, detail="Database is currently unreachable.") from e

@router.delete("/{item_id}")
def remove_from_watchlist(item_id: uuid.UUID, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_or_create_profile(db, user)
    try:
        item = db.query(Watchlist).filter(Watchlist.id == item_id, Watchlist.user_id == profile.id).first()
        
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
            
        db.delete(item)
        db.commit()
        return {"status": "success", "detail": "Item removed from watchlist"}
    except sqlalchemy.exc.OperationalError as e:
        raise HTTPException(status_code=503, detail="Database is currently unreachable.") from e
