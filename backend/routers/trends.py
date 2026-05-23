from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import TrendPost, Genre
from ..services.x_api import search_trending

router = APIRouter(prefix="/api/trends", tags=["trends"])


@router.get("")
def get_trends(
    genre: Optional[Genre] = None,
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db),
):
    q = db.query(TrendPost)
    if genre:
        q = q.filter(TrendPost.genre == genre)
    posts = (
        q.order_by((TrendPost.likes + TrendPost.retweets * 2).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": p.id,
            "tweet_id": p.tweet_id,
            "genre": p.genre,
            "text": p.text,
            "author_username": p.author_username,
            "author_name": p.author_name,
            "author_image": p.author_image,
            "likes": p.likes,
            "retweets": p.retweets,
            "replies": p.replies,
            "posted_at": p.posted_at.isoformat() if p.posted_at else None,
            "score": p.likes + p.retweets * 2,
        }
        for p in posts
    ]


@router.post("/refresh")
def refresh_trends(genre: Genre, db: Session = Depends(get_db)):
    try:
        tweets = search_trending(genre.value)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    added = 0
    for t in tweets:
        existing = db.query(TrendPost).filter(TrendPost.tweet_id == t["tweet_id"]).first()
        if existing:
            existing.likes = t["likes"]
            existing.retweets = t["retweets"]
            existing.replies = t["replies"]
        else:
            trend = TrendPost(genre=genre, **t)
            db.add(trend)
            added += 1
    db.commit()
    return {"added": added, "total": len(tweets)}
