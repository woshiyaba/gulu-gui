from typing import Any

import anyio
from fastapi import HTTPException, status
from requests import RequestException

from api.repositories import wx_repository
from wx import WxMiniProgramClient, WxMiniProgramError


async def ensure_wx_auth_tables() -> None:
    await wx_repository.ensure_wx_auth_tables()


async def login_by_code(code: str) -> dict[str, Any]:
    js_code = (code or "").strip()
    if not js_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="code不能为空")

    try:
        session_data = await anyio.to_thread.run_sync(WxMiniProgramClient().code2session, js_code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except WxMiniProgramError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errcode": exc.errcode, "errmsg": exc.errmsg},
        ) from exc
    except RequestException as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="微信登录接口调用失败") from exc

    openid = (session_data.get("openid") or "").strip()
    if not openid:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="微信登录接口未返回openid")

    return await wx_repository.bind_wx_session(session_data)
