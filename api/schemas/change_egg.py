from datetime import datetime

from pydantic import BaseModel, Field


class ChangeEggCreateRequest(BaseModel):
    """新增换蛋挂单：拥有(pokemon_id+tag) + 需求(pokemon_id+tag) + 游戏 id。"""

    user_id: int = Field(..., description="平台用户 id")
    game_id: str = Field("", max_length=64, description="游戏 id（长串数字）")
    own_pokemon_id: int = Field(..., description="拥有的精灵 id（pokemon.id）")
    own_tag: str = Field("", max_length=30, description="拥有蛋组的 tag code")
    want_pokemon_id: int = Field(..., description="需求的精灵 id（pokemon.id）")
    want_tag: str = Field("", max_length=30, description="需求蛋组的 tag code")


class ChangeEggListing(BaseModel):
    """一条换蛋挂单（含 own/want 对应 pokemon 的展示信息）。"""

    id: int
    user_id: int
    game_id: str = ""
    own_pokemon_id: int
    own_tag: str = ""
    want_pokemon_id: int
    want_tag: str = ""
    status: str = "open"
    own_pokemon_name: str | None = None
    own_pokemon_avatar: str | None = None
    want_pokemon_name: str | None = None
    want_pokemon_avatar: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ChangeEggCloseRequest(BaseModel):
    """主动关闭自己正在匹配的挂单。"""

    user_id: int = Field(..., description="平台用户 id（校验归属）")


class ChangeEggTag(BaseModel):
    """换蛋蛋组 tag 选项。"""

    code: str
    label: str
    sort_order: int = 0
