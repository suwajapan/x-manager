from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from ..database import get_db
from ..models import Account, Analytics, Genre
from ..services.x_api import get_user_info

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class AccountCreate(BaseModel):
    username: str
    genre: Genre
    access_token: Optional[str] = None
    access_token_secret: Optional[str] = None


@router.get("")
def list_accounts(db: Session = Depends(get_db)):
    accounts = db.query(Account).all()
    return [
        {
            "id": a.id,
            "username": a.username,
            "display_name": a.display_name,
            "profile_image_url": a.profile_image_url,
            "genre": a.genre,
            "followers": a.followers,
            "following": a.following,
            "tweet_count": a.tweet_count,
            "has_token": bool(a.access_token and a.access_token_secret),
        }
        for a in accounts
    ]


@router.post("")
def create_account(body: AccountCreate, db: Session = Depends(get_db)):
    existing = db.query(Account).filter(Account.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="すでに登録済みのアカウントです")

    info = get_user_info(body.username)
    if not info:
        raise HTTPException(status_code=404, detail="X アカウントが見つかりません")

    account = Account(
        username=body.username,
        genre=body.genre,
        access_token=body.access_token,
        access_token_secret=body.access_token_secret,
        **info,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return {"id": account.id, "username": account.username}


@router.delete("/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="アカウントが見つかりません")
    db.delete(account)
    db.commit()
    return {"ok": True}


@router.get("/{account_id}/analytics")
def get_analytics(account_id: int, db: Session = Depends(get_db)):
    records = (
        db.query(Analytics)
        .filter(Analytics.account_id == account_id)
        .order_by(Analytics.recorded_at.desc())
        .limit(30)
        .all()
    )
    return [
        {
            "followers": r.followers,
            "following": r.following,
            "tweet_count": r.tweet_count,
            "recorded_at": r.recorded_at.isoformat(),
        }
        for r in reversed(records)
    ]
