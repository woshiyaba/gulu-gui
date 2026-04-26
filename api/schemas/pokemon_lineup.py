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
    resonance_magic_id: int | None = None
    resonance_magic_name: str = ""
    resonance_magic_icon: str = ""
    sort_order: int = 0
    is_active: bool = True
    members: list[PokemonLineupMemberItem] = Field(default_factory=list)


class PokemonLineupListItem(BaseModel):
    id: int
    title: str = ""
    source_type: str = ""
    resonance_magic_id: int | None = None
    resonance_magic_name: str = ""
    resonance_magic_icon: str = ""
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
    resonance_magic_id: int | None = None
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


# ── 用户对战 PK 请求/响应 ────────────────────────────────
# 前端用户配置队伍后直接提交（无需先存为 ops 阵容），字段尽量宽松。
class BattlePkMember(BaseModel):
    pokemon_id: int | None = None
    pokemon_name: str = ""
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
    skill_2_id: int | None = None
    skill_2_name: str = ""
    skill_3_id: int | None = None
    skill_3_name: str = ""
    skill_4_id: int | None = None
    skill_4_name: str = ""
    member_desc: str = ""


class BattlePkTeam(BaseModel):
    title: str = ""
    lineup_desc: str = ""
    source_type: str = ""
    resonance_magic_id: int | None = None
    resonance_magic_name: str = ""
    members: list[BattlePkMember] = Field(default_factory=list, max_length=6)


class BattlePkRequest(BaseModel):
    team_a: BattlePkTeam
    team_b: BattlePkTeam


class BattlePkVerdict(BaseModel):
    winner: str = "DRAW"
    win_rate_a: int = 50
    reason: str = ""


class BattlePkSide(BaseModel):
    summary: str = ""
    advantages: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class BattlePkRound(BaseModel):
    round: int
    desc: str = ""


class BattlePkCompleteness(BaseModel):
    ok: bool = True
    missing: list[str] = Field(default_factory=list)


class BattlePkPlan(BaseModel):
    team_a_order: list[str] = Field(default_factory=list)
    team_a_order_reason: str = ""
    team_b_order: list[str] = Field(default_factory=list)
    team_b_order_reason: str = ""
    skill_matchup: list[str] = Field(default_factory=list)
    ability_impact: list[str] = Field(default_factory=list)


class BattlePkResponse(BaseModel):
    completeness: BattlePkCompleteness = Field(default_factory=BattlePkCompleteness)
    plan: BattlePkPlan = Field(default_factory=BattlePkPlan)
    team_a: BattlePkSide = Field(default_factory=BattlePkSide)
    team_b: BattlePkSide = Field(default_factory=BattlePkSide)
    key_rounds: list[BattlePkRound] = Field(default_factory=list)
    turning_points: list[str] = Field(default_factory=list)
    verdict: BattlePkVerdict = Field(default_factory=BattlePkVerdict)
    error: str = ""
    raw: str = ""


# ── 公开字典 / 共鸣魔法选项 ─────────────────────────────
class BloodlineOption(BaseModel):
    id: int
    code: str = ""
    label: str = ""


class ResonanceMagicOption(BaseModel):
    id: int
    name: str
    description: str = ""
    icon_url: str = ""
    max_usage_count: int = 0
