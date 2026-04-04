from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.models import Asset, User
from database.session import get_db
from routers.auth_router import get_current_user


class CreateAssetPayload(BaseModel):
    asset_name: str
    purchase_price: float
    purchase_year: int
    rate_per_year: float = 0
    notes: str | None = None


class UpdateAssetPayload(BaseModel):
    asset_name: str | None = None
    purchase_price: float | None = None
    purchase_year: int | None = None
    rate_per_year: float | None = None
    notes: str | None = None


router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("/")
def get_assets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    assets = db.query(Asset).filter(Asset.user_id == current_user.id).all()
    
    asset_list = []
    for a in assets:
        asset_list.append({
            "id": a.id,
            "asset_name": a.asset_name,
            "purchase_price": a.purchase_price,
            "purchase_year": a.purchase_year,
            "rate_per_year": a.rate_per_year,
            "notes": a.notes,
            "created_at": a.created_at.isoformat() if a.created_at else None
        })
        
    return {"assets": asset_list}


@router.post("/")
def create_asset(
    payload: CreateAssetPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    asset = Asset(
        user_id=current_user.id,
        asset_name=payload.asset_name,
        purchase_price=payload.purchase_price,
        purchase_year=payload.purchase_year,
        rate_per_year=payload.rate_per_year,
        notes=payload.notes,
    )
    db.add(asset)
    db.commit()
    
    return get_assets(db, current_user)


@router.delete("/{asset_id}")
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == current_user.id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    
    db.delete(asset)
    db.commit()
    return get_assets(db, current_user)
