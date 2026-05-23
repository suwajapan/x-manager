import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

GENRE_PERSONA = {
    "food": "ご飯・グルメ系のSNS運用者",
    "beauty": "美容・コスメ系のSNS運用者",
    "fashion": "ファッション・コーデ系のSNS運用者",
}


def generate_post(genre: str, inspiration_tweets: list[str], instruction: str = "") -> str:
    genre_label = GENRE_PERSONA.get(genre, "SNS運用者")
    examples = "\n".join(f"- {t}" for t in inspiration_tweets[:3])

    prompt = f"""あなたは{genre_label}です。
以下のバズっているポストをインスピレーションにして、Xに投稿する新しいポスト文を1つ作成してください。

【参考にするポスト】
{examples}

【追加の指示】
{instruction if instruction else "なし"}

【条件】
- 140文字以内
- 絵文字を適度に使用
- 読者が共感・保存・RTしたくなる内容
- 参考ポストのコピーはNG、あくまでインスピレーション
- ポスト文のみ出力（説明不要）"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()
