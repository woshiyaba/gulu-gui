from pydantic import BaseModel, Field


class AttributeItem(BaseModel):
    attr_name: str
    attr_image: str


class PokemonListItem(BaseModel):
    no: str
    name: str
    image_url: str
    type: str
    type_name: str
    form: str
    form_name: str
    attributes: list[AttributeItem] = Field(default_factory=list)


class PokemonListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[PokemonListItem] = Field(default_factory=list)


class PokemonBodyMatchItem(BaseModel):
    pet_name: str


class PokemonBodyMatchResponse(BaseModel):
    height_m: float
    weight_kg: float
    height_cm: int
    weight_g: int
    total: int
    items: list[PokemonBodyMatchItem] = Field(default_factory=list)


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


class PokemonDetailResponse(PokemonListItem):
    obtain_method: str = ""
    stats: PokemonStats = Field(default_factory=PokemonStats)
    trait: PokemonTrait = Field(default_factory=PokemonTrait)
    restrain: PokemonRestrain = Field(default_factory=PokemonRestrain)
    skills: list[PokemonSkill] = Field(default_factory=list)
