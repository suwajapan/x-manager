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
    limit: int = Query(50, le=100),
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

    # ジャンルの古いデータを全削除して入れ直す
    db.query(TrendPost).filter(TrendPost.genre == genre).delete()
    db.commit()

    for t in tweets:
        trend = TrendPost(genre=genre, **t)
        db.add(trend)
    db.commit()
    return {"added": len(tweets), "total": len(tweets)}
