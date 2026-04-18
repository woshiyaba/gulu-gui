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


class OpsFriendImageUploadResponse(BaseModel):
    image_lc: str
    preview_url: str


class OpsPokemonSkillItem(BaseModel):
    skill_id: int
    type: str = "原生技能"
    sort_order: int = 0


class OpsPokemonUpsertRequest(BaseModel):
    no: str
    name: str
    image: str = ""
    type: str = ""
    type_name: str = ""
    form: str = ""
    form_name: str = ""
    egg_group: str = ""
    trait_id: int
    detail_url: str = ""
    image_lc: str = ""
    chain_id: int | None = None
    hp: int = 0
    atk: int = 0
    matk: int = 0
    def_val: int = 0
    mdef: int = 0
    spd: int = 0
    total_race: int = 0
    obtain_method: str = ""
    attribute_ids: list[int] = Field(default_factory=list)
    egg_groups: list[str] = Field(default_factory=list)
    skills: list[OpsPokemonSkillItem] = Field(default_factory=list)


class OpsPokemonListItem(BaseModel):
    id: int
    no: str
    name: str
    type_name: str = ""
    form_name: str = ""
    trait_name: str = ""
    attributes: list[str] = Field(default_factory=list)
    egg_groups: list[str] = Field(default_factory=list)


class OpsPokemonListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 10
    items: list[OpsPokemonListItem] = Field(default_factory=list)


class OpsPokemonDetailResponse(BaseModel):
    id: int
    no: str
    name: str
    image: str = ""
    type: str = ""
    type_name: str = ""
    form: str = ""
    form_name: str = ""
    egg_group: str = ""
    trait_id: int
    detail_url: str = ""
    image_lc: str = ""
    chain_id: int | None = None
    hp: int = 0
    atk: int = 0
    matk: int = 0
    def_val: int = 0
    mdef: int = 0
    spd: int = 0
    total_race: int = 0
    obtain_method: str = ""
    attribute_ids: list[int] = Field(default_factory=list)
    egg_groups: list[str] = Field(default_factory=list)
    skills: list[OpsPokemonSkillItem] = Field(default_factory=list)


class OpsPokemonOptionItem(BaseModel):
    id: int
    name: str
    icon: str = ""


class OpsPokemonOptionsResponse(BaseModel):
    attributes: list[OpsPokemonOptionItem] = Field(default_factory=list)
    traits: list[OpsPokemonOptionItem] = Field(default_factory=list)
    skills: list[OpsPokemonOptionItem] = Field(default_factory=list)
    skill_sources: list[str] = Field(default_factory=lambda: ["原生技能", "学习技能"])


class OpsEvolutionChainStepItem(BaseModel):
    sort_order: int
    pokemon_name: str
    evolution_condition: str = ""
    image_url: str = ""
    matched: bool = False


class OpsEvolutionChainResponse(BaseModel):
    chain_id: int | None = None
    steps: list[OpsEvolutionChainStepItem] = Field(default_factory=list)


class OpsEvolutionChainUpsertRequest(BaseModel):
    steps: list[OpsEvolutionChainStepItem] = Field(default_factory=list)


class OpsSkillListItem(BaseModel):
    id: int
    name: str
    attr: str = ""
    type: str = ""
    power: int = 0
    consume: int = 0
    skill_desc: str = ""
    icon: str = ""
    icon_url: str = ""


class OpsSkillListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 10
    items: list[OpsSkillListItem] = Field(default_factory=list)


class OpsSkillDetailResponse(OpsSkillListItem):
    pass


class OpsSkillUpsertRequest(BaseModel):
    name: str
    attr: str = ""
    type: str = ""
    power: int = 0
    consume: int = 0
    skill_desc: str = ""
    icon: str = ""


class OpsSkillUsageItem(BaseModel):
    id: int
    no: str
    name: str
    type: str = "原生技能"
    sort_order: int = 0


class OpsSkillUsageResponse(BaseModel):
    total: int
    items: list[OpsSkillUsageItem] = Field(default_factory=list)


class OpsSkillOptionsResponse(BaseModel):
    attrs: list[str] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)


class OpsSkillIconUploadResponse(BaseModel):
    icon: str
    preview_url: str
