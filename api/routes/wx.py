from fastapi import APIRouter

from api.schemas.wx import WxLoginRequest, WxLoginResponse
from api.services import wx_service

router = APIRouter(prefix="/api/wx", tags=["wx"])


@router.post("/login", response_model=WxLoginResponse)
async def wx_login(payload: WxLoginRequest):
    return await wx_service.login_by_code(payload.code)
