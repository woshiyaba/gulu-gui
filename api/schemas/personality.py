from pydantic import BaseModel, Field


class PersonalityItem(BaseModel):
    id: int
    name_en: str
    name_zh: str
    hp_mod_pct: float = 0.0
    phy_atk_mod_pct: float = 0.0
    mag_atk_mod_pct: float = 0.0
    phy_def_mod_pct: float = 0.0
    mag_def_mod_pct: float = 0.0
    spd_mod_pct: float = 0.0
    buff_stat: str | None = None
    nerf_stat: str | None = None
    is_neutral: bool = False


class PersonalityListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 100
    items: list[PersonalityItem] = Field(default_factory=list)


class PersonalityUpsertRequest(BaseModel):
    id: int | None = None
    name_en: str
    name_zh: str
    hp_mod_pct: float = 0.0
    phy_atk_mod_pct: float = 0.0
    mag_atk_mod_pct: float = 0.0
    phy_def_mod_pct: float = 0.0
    mag_def_mod_pct: float = 0.0
    spd_mod_pct: float = 0.0


class PersonalityResetResponse(BaseModel):
    inserted: int
    source: str = "json"
