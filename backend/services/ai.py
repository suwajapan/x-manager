import os
import base64
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

GENRE_PERSONA = {
    "food": "ご飯・グルメ系のSNS運用者",
    "beauty": "美容・コスメ系のSNS運用者",
    "fashion": "ファッション・コーデ系のSNS運用者",
}

TASTE_LABEL = {
    "buzz":    "バズ狙い（いいね・保存されやすい、インパクト重視）",
    "empathy": "共感型（フォロワーが思わず反応したくなる、日常感・あるある）",
    "elegant": "上品・洗練（ハイブランド感、シンプルで洗練された文体）",
    "casual":  "親しみやすい（カジュアル・フレンドリー、会話口調）",
    "info":    "情報提供型（詳細・スペック・使い方を伝える）",
}


def generate_post(genre: str, inspiration_tweets: list, instruction: str = "") -> str:
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


def generate_caption(
    genre: str,
    taste: str,
    description: str,
    db_examples: list,
    image_data: bytes | None = None,
    image_media_type: str = "image/jpeg",
) -> str:
    genre_label = GENRE_PERSONA.get(genre, "SNS運用者")
    taste_label = TASTE_LABEL.get(taste, taste)
    examples_text = "\n".join(f"- {t}" for t in db_examples[:5]) if db_examples else "なし"

    text_prompt = f"""あなたは{genre_label}です。
{"添付の画像" if image_data else "以下の画像説明"}に合わせて、Xに投稿するキャプションを1つ生成してください。

【画像の詳細】
{description}

【テイスト】
{taste_label}

【参考にするバズ投稿（DBより）】
{examples_text}

【条件】
- 140文字以内
- 絵文字を適度に使用
- 画像の内容・雰囲気に合った文章
- テイストを意識した文体
- キャプション文のみ出力（説明不要）"""

    if image_data:
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_media_type,
                    "data": base64.standard_b64encode(image_data).decode("utf-8"),
                },
            },
            {"type": "text", "text": text_prompt},
        ]
    else:
        content = text_prompt

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": content}],
    )
    return message.content[0].text.strip()
