from fastapi import APIRouter, Depends
from sqlalchemy import func, extract
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ..database import get_db
from ..models import APIUsage

router = APIRouter(prefix="/api/costs", tags=["costs"])

X_READ_LIMIT = 10000   # Basic プラン月間読み取り上限
X_WRITE_LIMIT = 1500   # Basic プラン月間書き込み上限


@router.get("")
def get_costs(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    year, month = now.year, now.month

    def this_month(q):
        return q.filter(
            extract("year", APIUsage.called_at) == year,
            extract("month", APIUsage.called_at) == month,
        )

    # Anthropic 今月合計
    anthropic_rows = this_month(
        db.query(
            APIUsage.operation,
            func.sum(APIUsage.input_tokens).label("input"),
            func.sum(APIUsage.output_tokens).label("output"),
            func.sum(APIUsage.cost_usd).label("cost"),
            func.count().label("calls"),
        ).filter(APIUsage.service == "anthropic")
    ).group_by(APIUsage.operation).all()

    anthropic_total_cost = sum(r.cost for r in anthropic_rows)
    anthropic_breakdown = [
        {
            "operation": r.operation,
            "calls": r.calls,
            "input_tokens": r.input,
            "output_tokens": r.output,
            "cost_usd": round(r.cost / 1_000_000, 4),
        }
        for r in anthropic_rows
    ]

    # X API 今月カウント
    x_read_count = this_month(
        db.query(func.count()).filter(APIUsage.service == "x_read")
    ).scalar() or 0

    x_write_count = this_month(
        db.query(func.count()).filter(APIUsage.service == "x_write")
    ).scalar() or 0

    # 日別コスト（過去30日）
    daily = (
        db.query(
            func.date(APIUsage.called_at).label("date"),
            func.sum(APIUsage.cost_usd).label("cost"),
        )
        .filter(APIUsage.service == "anthropic")
        .group_by(func.date(APIUsage.called_at))
        .order_by(func.date(APIUsage.called_at))
        .limit(30)
        .all()
    )

    return {
        "month": f"{year}/{month:02d}",
        "anthropic": {
            "total_cost_usd": round(anthropic_total_cost / 1_000_000, 4),
            "breakdown": anthropic_breakdown,
        },
        "x_api": {
            "read": {"used": x_read_count, "limit": X_READ_LIMIT, "pct": round(x_read_count / X_READ_LIMIT * 100, 1)},
            "write": {"used": x_write_count, "limit": X_WRITE_LIMIT, "pct": round(x_write_count / X_WRITE_LIMIT * 100, 1)},
            "plan": "Basic ($100/月)",
        },
        "daily": [{"date": str(r.date), "cost_usd": round(r.cost / 1_000_000, 4)} for r in daily],
    }
