from typing import Any

import requests

from config import WX_MINI_APPID, WX_MINI_SECRET


class WxMiniProgramError(Exception):
    """微信小程序接口调用失败。"""

    def __init__(self, errcode: int, errmsg: str, response: dict[str, Any] | None = None) -> None:
        self.errcode = errcode
        self.errmsg = errmsg
        self.response = response or {}
        super().__init__(f"WeChat Mini Program API error {errcode}: {errmsg}")


class WxMiniProgramClient:
    CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"
    GRANT_TYPE = "authorization_code"

    def __init__(
        self,
        appid: str | None = None,
        secret: str | None = None,
        timeout: float = 10,
    ) -> None:
        self.appid = (appid or WX_MINI_APPID).strip()
        self.secret = (secret or WX_MINI_SECRET).strip()
        self.timeout = timeout

        if not self.appid:
            raise ValueError("WX_MINI_APPID is required")
        if not self.secret:
            raise ValueError("WX_MINI_SECRET is required")

    def code2session(self, code: str) -> dict[str, Any]:
        """通过 wx.login 获取的 code 换取 openid、session_key、unionid 等信息。"""
        js_code = (code or "").strip()
        if not js_code:
            raise ValueError("code is required")

        response = requests.get(
            self.CODE2SESSION_URL,
            params={
                "appid": self.appid,
                "secret": self.secret,
                "js_code": js_code,
                "grant_type": self.GRANT_TYPE,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        errcode = int(data.get("errcode") or 0)
        if errcode != 0:
            raise WxMiniProgramError(errcode, data.get("errmsg", ""), data)

        return data
