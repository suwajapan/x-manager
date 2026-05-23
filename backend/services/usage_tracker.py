from datetime import datetime
from ..database import SessionLocal
from ..models import APIUsage

# claude-sonnet-4-6 料金 ($/1M tokens)
ANTHROPIC_INPUT_PRICE = 3.00
ANTHROPIC_OUTPUT_PRICE = 15.00


def track_anthropic(operation: str, input_tokens: int, output_tokens: int):
    cost_usd = (
        input_tokens * ANTHROPIC_INPUT_PRICE / 1_000_000
        + output_tokens * ANTHROPIC_OUTPUT_PRICE / 1_000_000
    )
    cost_micro = int(cost_usd * 1_000_000)

    db = SessionLocal()
    try:
        db.add(APIUsage(
            service="anthropic",
            operation=operation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_micro,
        ))
        db.commit()
    finally:
        db.close()


def track_x(operation: str, service: str = "x_read"):
    db = SessionLocal()
    try:
        db.add(APIUsage(service=service, operation=operation))
        db.commit()
    finally:
        db.close()
