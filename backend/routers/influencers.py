from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_db
from ..models import Influencer, InfluencerPost, Genre
from ..services.x_api import get_user_info, get_influencer_posts

router = APIRouter(prefix="/api/influencers", tags=["influencers"])


class InfluencerCreate(BaseModel):
    username: str
    genre: Optional[Genre] = None


def get_user_id(username: str) -> Optional[str]:
    import requests, os
    BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN", "")
    def auth(r):
        r.headers["Authorization"] = f"Bearer {BEARER_TOKEN}"
        return r
    res = requests.get(
        f"https://api.twitter.com/2/users/by/username/{username}",
        auth=auth,
        params={"user.fields": "id"},
    )
    if res.status_code != 200:
        return None
    data = res.json().get("data")
    return data["id"] if data else None


@router.get("")
def list_influencers(db: Session = Depends(get_db)):
    influencers = db.query(Influencer).all()
    return [
        {
            "id": inf.id,
            "username": inf.username,
            "display_name": inf.display_name,
            "profile_image_url": inf.profile_image_url,
            "genre": inf.genre,
            "followers": inf.followers,
            "post_count": len(inf.posts),
            "top_likes": max((p.likes for p in inf.posts), default=0),
        }
        for inf in influencers
    ]


@router.post("")
def add_influencer(body: InfluencerCreate, db: Session = Depends(get_db)):
    existing = db.query(Influencer).filter(Influencer.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="すでに登録済みです")

    info = get_user_info(body.username)
    if not info:
        raise HTTPException(status_code=404, detail="X アカウントが見つかりません")

    user_id = get_user_id(body.username)
    influencer = Influencer(
        username=body.username,
        display_name=info["display_name"],
        profile_image_url=info["profile_image_url"],
        followers=info["followers"],
        genre=body.genre,
        user_id=user_id,
    )
    db.add(influencer)
    db.commit()
    db.refresh(influencer)

    if user_id:
        try:
            posts = get_influencer_posts(user_id)
            for p in posts:
                post = InfluencerPost(influencer_id=influencer.id, **p)
                db.add(post)
            db.commit()
        except ValueError:
            pass

    return {"id": influencer.id, "username": influencer.username}


@router.delete("/{influencer_id}")
def delete_influencer(influencer_id: int, db: Session = Depends(get_db)):
    inf = db.query(Influencer).filter(Influencer.id == influencer_id).first()
    if not inf:
        raise HTTPException(status_code=404, detail="見つかりません")
    db.delete(inf)
    db.commit()
    return {"ok": True}


@router.post("/{influencer_id}/refresh")
def refresh_influencer(influencer_id: int, db: Session = Depends(get_db)):
    inf = db.query(Influencer).filter(Influencer.id == influencer_id).first()
    if not inf:
        raise HTTPException(status_code=404, detail="見つかりません")
    if not inf.user_id:
        raise HTTPException(status_code=400, detail="user_id が取得できていません")

    try:
        posts = get_influencer_posts(inf.user_id)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    added = 0
    for p in posts:
        existing = db.query(InfluencerPost).filter(InfluencerPost.tweet_id == p["tweet_id"]).first()
        if existing:
            existing.likes = p["likes"]
            existing.retweets = p["retweets"]
        else:
            post = InfluencerPost(influencer_id=inf.id, **p)
            db.add(post)
            added += 1
    db.commit()
    return {"added": added, "total": len(posts)}


@router.get("/{influencer_id}/posts")
def get_posts(influencer_id: int, db: Session = Depends(get_db)):
    posts = (
        db.query(InfluencerPost)
        .filter(InfluencerPost.influencer_id == influencer_id)
        .order_by((InfluencerPost.likes + InfluencerPost.retweets * 2).desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": p.id,
            "tweet_id": p.tweet_id,
            "text": p.text,
            "likes": p.likes,
            "retweets": p.retweets,
            "replies": p.replies,
            "posted_at": p.posted_at.isoformat() if p.posted_at else None,
        }
        for p in posts
    ]
