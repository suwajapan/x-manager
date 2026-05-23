import os
from typing import Optional, List
from datetime import datetime, timedelta, timezone
import requests
from requests_oauthlib import OAuth1

BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN", "")
API_KEY = os.environ.get("X_API_KEY", "")
API_SECRET = os.environ.get("X_API_SECRET", "")

GENRE_KEYWORDS = {
    "food": "(ご飯 OR グルメ OR 飯テロ OR レシピ OR カフェ OR ランチ OR 晩ごはん OR おうちごはん OR 食べ物) lang:ja",
    "beauty": "(美容 OR スキンケア OR メイク OR コスメ OR ネイル OR ヘアケア OR 美白 OR 保湿 OR プチプラコスメ) lang:ja",
    "fashion": "(コーデ OR ファッション OR OOTD OR 服 OR プチプラ OR トレンドコーデ OR 着回し OR ユニクロコーデ) lang:ja",
}

MIN_FAVES = 1000  # この閾値以上のいいねがある投稿を対象にする
SEARCH_DAYS = 7   # 過去何日分を対象にするか


def bearer_auth(r):
    r.headers["Authorization"] = f"Bearer {BEARER_TOKEN}"
    return r


def make_oauth1(access_token: str, access_token_secret: str) -> OAuth1:
    return OAuth1(API_KEY, API_SECRET, access_token, access_token_secret)


def search_trending(genre: str, max_results: int = 100) -> List[dict]:
    query = GENRE_KEYWORDS.get(genre, "")
    if not query:
        return []

    start_time = (datetime.now(timezone.utc) - timedelta(days=SEARCH_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")

    res = requests.get(
        "https://api.twitter.com/2/tweets/search/recent",
        auth=bearer_auth,
        params={
            "query": f"{query} -is:retweet",
            "max_results": max_results,
            "start_time": start_time,
            "tweet.fields": "created_at,public_metrics,author_id,text",
            "expansions": "author_id",
            "user.fields": "username,name,profile_image_url",
            "sort_order": "relevancy",
        },
    )
    if res.status_code != 200:
        raise ValueError(f"X API error {res.status_code}: {res.text}")

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

    # プラン制限で min_faves 演算子は使えないためローカルでスコア降順ソート
    result.sort(key=lambda x: x["likes"] + x["retweets"] * 2, reverse=True)
    return result


def get_influencer_posts(user_id: str, max_results: int = 20) -> List[dict]:
    res = requests.get(
        f"https://api.twitter.com/2/users/{user_id}/tweets",
        auth=bearer_auth,
        params={
            "max_results": max_results,
            "tweet.fields": "created_at,public_metrics,text",
            "exclude": "retweets,replies",
        },
    )
    if res.status_code != 200:
        raise ValueError(f"X API error {res.status_code}: {res.text}")
    tweets = res.json().get("data", [])
    result = []
    for t in tweets:
        m = t.get("public_metrics", {})
        result.append({
            "tweet_id": t["id"],
            "text": t["text"],
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


def post_tweet(access_token: str, access_token_secret: str, content: str) -> dict:
    oauth = make_oauth1(access_token, access_token_secret)
    res = requests.post(
        "https://api.twitter.com/2/tweets",
        auth=oauth,
        json={"text": content},
    )
    return res.json()
