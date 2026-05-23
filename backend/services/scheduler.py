from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import ScheduledPost, PostStatus, Account, TrendPost, Analytics, Genre
from .x_api import search_trending, get_user_info, post_tweet

scheduler = BackgroundScheduler()


def publish_scheduled_posts():
    db: Session = SessionLocal()
    now = datetime.now(timezone.utc)
    posts = (
        db.query(ScheduledPost)
        .filter(
            ScheduledPost.status == PostStatus.scheduled,
            ScheduledPost.scheduled_at <= now,
        )
        .all()
    )
    for post in posts:
        account: Account = post.account
        if not account.access_token or not account.access_token_secret:
            post.status = PostStatus.failed
            post.error_message = "access_token / access_token_secret が設定されていません"
            db.commit()
            continue

        result = post_tweet(account.access_token, account.access_token_secret, post.content)
        if "data" in result:
            post.status = PostStatus.published
            post.published_at = now
            post.tweet_id = result["data"]["id"]
        else:
            post.status = PostStatus.failed
            post.error_message = str(result)

        db.commit()
    db.close()


def fetch_trends():
    db: Session = SessionLocal()
    for genre in Genre:
        tweets = search_trending(genre.value, max_results=20)
        for t in tweets:
            existing = db.query(TrendPost).filter(TrendPost.tweet_id == t["tweet_id"]).first()
            if existing:
                existing.likes = t["likes"]
                existing.retweets = t["retweets"]
                existing.replies = t["replies"]
            else:
                trend = TrendPost(genre=genre, **t)
                db.add(trend)
        db.commit()
    db.close()


def record_analytics():
    db: Session = SessionLocal()
    accounts = db.query(Account).all()
    for account in accounts:
        info = get_user_info(account.username)
        if info:
            account.followers = info["followers"]
            account.following = info["following"]
            account.tweet_count = info["tweet_count"]
            analytics = Analytics(
                account_id=account.id,
                followers=info["followers"],
                following=info["following"],
                tweet_count=info["tweet_count"],
            )
            db.add(analytics)
    db.commit()
    db.close()


def start():
    scheduler.add_job(publish_scheduled_posts, IntervalTrigger(minutes=1), id="publish")
    scheduler.add_job(fetch_trends, IntervalTrigger(hours=1), id="trends")
    scheduler.add_job(record_analytics, IntervalTrigger(hours=6), id="analytics")
    scheduler.start()
