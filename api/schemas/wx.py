from pydantic import BaseModel


class WxLoginRequest(BaseModel):
    code: str


class WxLoginResponse(BaseModel):
    user_id: int
    social_member_id: int
    openid: str
    session_key: str = ""
    unionid: str = ""
    is_new_user: bool = False
