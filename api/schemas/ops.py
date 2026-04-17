from pydantic import BaseModel, Field


class OpsLoginRequest(BaseModel):
    username: str
    password: str


class OpsUserInfo(BaseModel):
    id: int
    username: str
    nickname: str
    role: str


class OpsLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: OpsUserInfo


class OpsDictItem(BaseModel):
    id: int
    dict_type: str
    code: str
    label: str
    sort_order: int = 0


class OpsDictListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 10
    items: list[OpsDictItem] = Field(default_factory=list)


class OpsDictUpsertRequest(BaseModel):
    dict_type: str
    code: str
    label: str
    sort_order: int = 0


class OpsProfileUpdateRequest(BaseModel):
    nickname: str = ""
    current_password: str = ""
    new_password: str = ""


class OpsUserCreateRequest(BaseModel):
    username: str
    nickname: str = ""
    password: str
    role: str = "editor"


class OpsUserUpdateRequest(BaseModel):
    nickname: str = ""
    password: str = ""
    role: str = "editor"


class OpsUserListResponse(BaseModel):
    items: list[OpsUserInfo] = Field(default_factory=list)
