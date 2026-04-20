from pydantic import BaseModel, Field


class StarlightDuelPetInput(BaseModel):
    pet_id: int
    sort_order: int = 1
    skill_1_id: int | None = None
    skill_2_id: int | None = None
    skill_3_id: int | None = None
    skill_4_id: int | None = None


class StarlightDuelPetItem(BaseModel):
    id: int
    pet_id: int
    pet_name: str = ""
    pet_image: str = ""
    sort_order: int = 1
    skill_1_id: int | None = None
    skill_1_name: str = ""
    skill_2_id: int | None = None
    skill_2_name: str = ""
    skill_3_id: int | None = None
    skill_3_name: str = ""
    skill_4_id: int | None = None
    skill_4_name: str = ""


class StarlightDuelEpisodeDetail(BaseModel):
    id: int
    episode_number: int
    title: str = ""
    strategy_text: str = ""
    is_active: bool = True
    pets: list[StarlightDuelPetItem] = Field(default_factory=list)


class StarlightDuelEpisodeListItem(BaseModel):
    id: int
    episode_number: int
    title: str = ""
    is_active: bool = True


class StarlightDuelEpisodeListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 10
    items: list[StarlightDuelEpisodeListItem] = Field(default_factory=list)


class StarlightDuelEpisodeUpsertRequest(BaseModel):
    episode_number: int
    title: str = ""
    strategy_text: str = ""
    is_active: bool = True
    pets: list[StarlightDuelPetInput] = Field(default_factory=list)


class StarlightDuelSearchItem(BaseModel):
    id: int
    name: str
    image: str = ""


class StarlightDuelSearchResponse(BaseModel):
    items: list[StarlightDuelSearchItem] = Field(default_factory=list)
