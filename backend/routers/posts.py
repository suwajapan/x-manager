from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from ..database import get_db
from ..models import ScheduledPost, PostStatus, Account, InfluencerPost, Influencer, Genre
from ..services.ai import generate_post, generate_caption

router = APIRouter(prefix="/api/posts", tags=["posts"])


class PostCreate(BaseModel):
    account_id: int
    content: str
    scheduled_at: Optional[datetime] = None


class GenerateRequest(BaseModel):
    genre: str
    inspiration_texts: List[str]
    instruction: str = ""


@router.get("")
def list_posts(
    account_id: Optional[int] = None,
    status: Optional[PostStatus] = None,
    db: Session = Depends(get_db),
):
    q = db.query(ScheduledPost)
    if account_id:
        q = q.filter(ScheduledPost.account_id == account_id)
    if status:
        q = q.filter(ScheduledPost.status == status)
    posts = q.order_by(ScheduledPost.created_at.desc()).limit(100).all()
    return [
        {
            "id": p.id,
            "account_id": p.account_id,
            "account_username": p.account.username if p.account else None,
            "content": p.content,
            "status": p.status,
            "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
            "published_at": p.published_at.isoformat() if p.published_at else None,
            "tweet_id": p.tweet_id,
            "error_message": p.error_message,
        }
        for p in posts
    ]


@router.post("")
def create_post(body: PostCreate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == body.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="アカウントが見つかりません")

    status = PostStatus.scheduled if body.scheduled_at else PostStatus.draft
    post = ScheduledPost(
        account_id=body.account_id,
        content=body.content,
        scheduled_at=body.scheduled_at,
        status=status,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"id": post.id, "status": post.status}


@router.put("/{post_id}")
def update_post(post_id: int, body: PostCreate, db: Session = Depends(get_db)):
    post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="投稿が見つかりません")
    if post.status == PostStatus.published:
        raise HTTPException(status_code=400, detail="公開済みの投稿は編集できません")

    post.content = body.content
    post.scheduled_at = body.scheduled_at
    post.status = PostStatus.scheduled if body.scheduled_at else PostStatus.draft
    db.commit()
    return {"id": post.id, "status": post.status}


@router.delete("/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="投稿が見つかりません")
    db.delete(post)
    db.commit()
    return {"ok": True}


@router.post("/generate")
def generate(body: GenerateRequest):
    text = generate_post(body.genre, body.inspiration_texts, body.instruction)
    return {"content": text}


@router.post("/generate-caption")
async def generate_caption_endpoint(
    genre: str = Form(...),
    taste: str = Form(...),
    description: str = Form(""),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    # DB からそのジャンルのバズ投稿を取得（参考用）
    db_posts = (
        db.query(InfluencerPost)
        .join(Influencer)
        .filter(Influencer.genre == genre)
        .order_by((InfluencerPost.likes + InfluencerPost.retweets * 2).desc())
        .limit(5)
        .all()
    )
    db_examples = [p.text for p in db_posts]

    image_data = None
    image_media_type = "image/jpeg"
    if image and image.filename:
        image_data = await image.read()
        image_media_type = image.content_type or "image/jpeg"

    caption = generate_caption(
        genre=genre,
        taste=taste,
        description=description,
        db_examples=db_examples,
        image_data=image_data,
        image_media_type=image_media_type,
    )
    return {"content": caption}
