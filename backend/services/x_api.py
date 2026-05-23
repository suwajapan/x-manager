import os
from typing import Optional
import requests

BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN", "")
CLIENT_ID = os.environ.get("X_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("X_CLIENT_SECRET", "")

GENRE_KEYWORDS = {
    "food": "(ご飯 OR グルメ OR 飯テロ OR レシピ OR カフェ OR ランチ OR 晩ごはん) lang:ja",
    "beauty": "(美容 OR スキンケア OR メイク OR コスメ OR ネイル OR ヘアケア) lang:ja",
    "fashion": "(コーデ OR ファッション OR OOTD OR 服 OR プチプラ OR トレンドコーデ) lang:ja",
}


def bearer_auth(r):
    r.headers["Authorization"] = f"Bearer {BEARER_TOKEN}"
    return r


def search_trending(genre: str, max_results: int = 20) -> list[dict]:
    query = GENRE_KEYWORDS.get(genre, "")
    if not query:
        return []

    res = requests.get(
        "https://api.twitter.com/2/tweets/search/recent",
        auth=bearer_auth,
        params={
            "query": f"{query} -is:retweet has:images",
            "max_results": max_results,
            "tweet.fields": "created_at,public_metrics,author_id,text",
            "expansions": "author_id",
            "user.fields": "username,name,profile_image_url",
            "sort_order": "relevancy",
        },
    )
    if res.status_code != 200:
        return []

    data = res.json()
    tweets = data.get("data", [])
    users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

    result = []
    for t in tweets:
        author = users.get(t["author_id"], {})
        m = t.get("public_metrics", {})
        result.append({
            "tweet_id": t["id"],
            "text": t["text"],
            "author_username": author.get("username", ""),
            "author_name": author.get("name", ""),
            "author_image": author.get("profile_image_url", ""),
            "likes": m.get("like_count", 0),
            "retweets": m.get("retweet_count", 0),
            "replies": m.get("reply_count", 0),
            "posted_at": t.get("created_at"),
        })

    result.sort(key=lambda x: x["likes"] + x["retweets"] * 2, reverse=True)
    return result


def get_user_info(username: str) -> Optional[dict]:
    res = requests.get(
        f"https://api.twitter.com/2/users/by/username/{username}",
        auth=bearer_auth,
        params={"user.fields": "id,name,username,description,public_metrics,profile_image_url"},
    )
    if res.status_code != 200:
        return None
    data = res.json().get("data")
    if not data:
        return None
    m = data.get("public_metrics", {})
    return {
        "display_name": data["name"],
        "profile_image_url": data.get("profile_image_url", ""),
        "followers": m.get("followers_count", 0),
        "following": m.get("following_count", 0),
        "tweet_count": m.get("tweet_count", 0),
    }


def post_tweet(access_token: str, content: str) -> dict:
    res = requests.post(
        "https://api.twitter.com/2/tweets",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={"text": content},
    )
    return res.json()


def refresh_access_token(refresh_token: str) -> Optional[dict]:
    res = requests.post(
        "https://api.twitter.com/2/oauth2/token",
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )
    if res.status_code != 200:
        return None
    return res.json()
