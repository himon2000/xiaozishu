import base64
import binascii

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from dependencies import get_current_user
from models import User
from services.content_security import (
    ContentCheckUnavailableError,
    ContentRejectedError,
    ensure_safe_image,
)

router = APIRouter(prefix="/api/v1/content-security", tags=["内容安全"])


class ImageCheckRequest(BaseModel):
    image_base64: str = Field(..., max_length=1500000)
    content_type: str = Field(pattern="^image/(jpeg|png)$")


@router.post("/image")
def check_image(body: ImageCheckRequest, user: User = Depends(get_current_user)):
    try:
        content = base64.b64decode(body.image_base64, validate=True)
        ensure_safe_image(content, body.content_type)
    except ContentRejectedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ContentCheckUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail="图片数据无效") from exc
    return {"success": True}
