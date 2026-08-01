from fastapi import HTTPException

from services.content_security import (
    ContentCheckUnavailableError,
    ContentRejectedError,
    ensure_safe_text,
)


def guard_user_content(openid: str, *values) -> None:
    try:
        ensure_safe_text(openid, *values)
    except ContentRejectedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ContentCheckUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
