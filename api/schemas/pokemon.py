from pydantic import BaseModel, Field


class AttributeItem(BaseModel):
    attr_name: str
    attr_image: str


class CategoryItem(BaseModel):
    id: int
    category_id: int
    description: str | None = None
    type: str | None = None


class PokemonListItem(BaseModel):
    no: str
    name: str
    image_url: str
    type: str
    type_name: str
    form: str
    form_name: str
    attributes: list[AttributeItem] = Field(default_factory=list)
    egg_groups: list[str] = Field(default_factory=list)


class PokemonListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[PokemonListItem] = Field(default_factory=list)


class SkillStoneItem(BaseModel):
    skill_name: str
    obtain_method: str = ""
    icon: str = ""


class SkillStoneListResponse(BaseModel):
    total: int
    items: list[SkillStoneItem] = Field(default_factory=list)


class PokemonBodyMatchItem(BaseModel):
    pet_name: str
    image_url: str


class PokemonBodyMatchResponse(BaseModel):
    height_m: float
    weight_kg: float
    height_cm: int
    weight_g: int
    total: int
    items: list[PokemonBodyMatchItem] = Field(default_factory=list)


class PetMapPointItem(BaseModel):
    id: int
    source_id: int
    map_id: int
    title: str = ""
    latitude: float
    longitude: float
    category_id: int
    category_image_url: str


class EvolutionChainItem(BaseModel):
    name: str
    image_url: str = ""


class EvolutionChainStage(BaseModel):
    sort_order: int
    next_condition: str = ""
    items: list[EvolutionChainItem] = Field(default_factory=list)


class PokemonEvolutionChainResponse(BaseModel):
    chain_id: int | None = None
    stages: list[EvolutionChainStage] = Field(default_factory=list)


class PokemonStats(BaseModel):
    hp: int = 0
    atk: int = 0
    matk: int = 0
    def_val: int = 0
    mdef: int = 0
    spd: int = 0


class PokemonTrait(BaseModel):
    name: str = ""
    desc: str = ""


class PokemonRestrain(BaseModel):
    strong_against: list[str] = Field(default_factory=list)
    weak_against: list[str] = Field(default_factory=list)
    resist: list[str] = Field(default_factory=list)
    resisted: list[str] = Field(default_factory=list)


class PokemonSkill(BaseModel):
    name: str
    attr: str = ""
    power: int = 0
    type: str = ""
    consume: int = 0
    desc: str = ""
    icon: str = ""


class SkillListResponse(BaseModel):
    total: int
    items: list[PokemonSkill] = Field(default_factory=list)


class DefensiveTypeChartCell(BaseModel):
    attacker_attr: str
    multiplier: float
    label: str
    bucket: str = "neutral"


class DefensiveTypeChart(BaseModel):
    """精灵受各「进攻招式属性」技能时的伤害倍率（双属性为单方倍率相乘）。"""

    defender_attrs: list[str] = Field(default_factory=list)
    cells: list[DefensiveTypeChartCell] = Field(default_factory=list)


class PokemonDetailResponse(PokemonListItem):
    obtain_method: str = ""
    stats: PokemonStats = Field(default_factory=PokemonStats)
    trait: PokemonTrait = Field(default_factory=PokemonTrait)
    restrain: PokemonRestrain = Field(default_factory=PokemonRestrain)
    skills: list[PokemonSkill] = Field(default_factory=list)
    defensive_type_chart: DefensiveTypeChart | None = None
