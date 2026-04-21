from pydantic import BaseModel, Field


class PokemonLineupMemberInput(BaseModel):
    pokemon_id: int
    sort_order: int = 1
    bloodline_dict_id: int | None = None
    personality_id: int | None = None
    qual_1: str = ""
    qual_2: str = ""
    qual_3: str = ""
    skill_1_id: int | None = None
    skill_2_id: int | None = None
    skill_3_id: int | None = None
    skill_4_id: int | None = None
    member_desc: str = ""


class PokemonLineupMemberItem(BaseModel):
    id: int
    pokemon_id: int
    pokemon_name: str = ""
    pokemon_image: str = ""
    sort_order: int = 1
    bloodline_dict_id: int | None = None
    bloodline_label: str = ""
    personality_id: int | None = None
    personality_name_zh: str = ""
    qual_1: str = ""
    qual_2: str = ""
    qual_3: str = ""
    skill_1_id: int | None = None
    skill_1_name: str = ""
    skill_1_image: str = ""
    skill_2_id: int | None = None
    skill_2_name: str = ""
    skill_2_image: str = ""
    skill_3_id: int | None = None
    skill_3_name: str = ""
    skill_3_image: str = ""
    skill_4_id: int | None = None
    skill_4_name: str = ""
    skill_4_image: str = ""
    member_desc: str = ""


class PokemonLineupDetail(BaseModel):
    id: int
    title: str = ""
    lineup_desc: str = ""
    source_type: str = ""
    sort_order: int = 0
    is_active: bool = True
    members: list[PokemonLineupMemberItem] = Field(default_factory=list)


class PokemonLineupListItem(BaseModel):
    id: int
    title: str = ""
    source_type: str = ""
    sort_order: int = 0
    is_active: bool = True
    member_count: int = 0


class PokemonLineupListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 10
    items: list[PokemonLineupListItem] = Field(default_factory=list)


class PokemonLineupUpsertRequest(BaseModel):
    title: str = ""
    lineup_desc: str = ""
    source_type: str = ""
    sort_order: int = 1
    is_active: bool = True
    members: list[PokemonLineupMemberInput] = Field(default_factory=list)


class PokemonLineupPublicList(BaseModel):
    items: list[PokemonLineupDetail] = Field(default_factory=list)


class PokemonLineupSearchItem(BaseModel):
    id: int
    name: str
    image: str = ""


class PokemonLineupSearchResponse(BaseModel):
    items: list[PokemonLineupSearchItem] = Field(default_factory=list)
