from typing import Literal

from pydantic import BaseModel, Field

# 六维属性键，对应 PokemonStats 字段
STAT_KEYS = ("hp", "atk", "matk", "def_val", "mdef", "spd")
STAT_LABELS = {
    "hp": "生命",
    "atk": "物攻",
    "matk": "魔攻",
    "def_val": "物防",
    "mdef": "魔防",
    "spd": "速度",
}
# 六维属性 -> 性格修正字段
STAT_TO_PERSONALITY_COL = {
    "hp": "hp_mod_pct",
    "atk": "phy_atk_mod_pct",
    "matk": "mag_atk_mod_pct",
    "def_val": "phy_def_mod_pct",
    "mdef": "mag_def_mod_pct",
    "spd": "spd_mod_pct",
}


class DamageStatRequest(BaseModel):
    """属性计算请求：接收宠物六维种族值 + 个体值勾选 + 性格 + 努力值。"""

    # 六维种族值
    hp: int = Field(..., ge=0, description="生命种族值")
    atk: int = Field(..., ge=0, description="物攻种族值")
    matk: int = Field(..., ge=0, description="魔攻种族值")
    def_val: int = Field(..., ge=0, description="物防种族值")
    mdef: int = Field(..., ge=0, description="魔防种族值")
    spd: int = Field(..., ge=0, description="速度种族值")

    # 用户任意勾选的三个属性，这些属性额外获得【个体值】=60，其余为 0
    iv_stats: list[str] = Field(
        default_factory=list,
        description="勾选获得个体值(=60)的属性键，最多三个；可选值：hp/atk/matk/def_val/mdef/spd",
    )

    # 性格（二选一传入，优先 id）
    personality_id: int | None = Field(None, description="性格 id")
    personality_name: str | None = Field(None, description="性格名称")

    level: int = Field(60, ge=1, le=100, description="宠物等级")

    # 努力值（先固定字段，提供默认值）
    hp_ev: int = Field(100, ge=0, description="生命努力值")
    atk_ev: int = Field(50, ge=0, description="物攻努力值")
    matk_ev: int = Field(50, ge=0, description="魔攻努力值")
    def_ev: int = Field(50, ge=0, description="物防努力值")
    mdef_ev: int = Field(50, ge=0, description="魔防努力值")
    spd_ev: int = Field(50, ge=0, description="速度努力值")


class DamageStatItem(BaseModel):
    key: str
    label: str
    base: int  # 种族值
    iv: int  # 个体值
    ev: int  # 努力值
    l: float  # L 系数（保留两位小数）
    nature_coef: float  # 性格系数
    value: int  # 真实属性值（四舍五入）


class DamageStatResponse(BaseModel):
    level: int
    personality_id: int | None = None
    personality_name: str = ""
    iv_value: int = 60
    iv_stats: list[str] = Field(default_factory=list)
    hp: DamageStatItem
    atk: DamageStatItem
    matk: DamageStatItem
    def_val: DamageStatItem
    mdef: DamageStatItem
    spd: DamageStatItem


# ── 伤害计算 ────────────────────────────────────────────────


class CombatStats(BaseModel):
    """参与伤害计算的宠物六维真实属性值。"""

    hp: int = Field(0, ge=0, description="生命")
    atk: int = Field(0, ge=0, description="物攻")
    matk: int = Field(0, ge=0, description="魔攻")
    def_val: int = Field(0, ge=0, description="物防")
    mdef: int = Field(0, ge=0, description="魔防")
    spd: int = Field(0, ge=0, description="速度")


class DamageCalcRequest(BaseModel):
    """技能伤害计算请求（PVP）。"""

    # 进攻方 / 被进攻方六维真实属性
    attacker: CombatStats
    defender: CombatStats

    # 连击次数
    combo_count: int = Field(1, ge=1, description="连击次数")

    # 威力来源：known=已知威力直接计算；base=按基础威力公式推导
    power_mode: Literal["known", "base"] = Field("known", description="威力计算模式")
    # 技能类别：决定使用物攻/物防 还是 魔攻/魔防
    skill_category: Literal["物攻", "魔攻"] = Field("物攻", description="技能类别")

    # ── known 模式 ──
    power: float | None = Field(None, ge=0, description="已知威力（known 模式必传）")

    # ── base 模式 ──
    skill_base_power: float | None = Field(None, ge=0, description="技能原威力（base 模式必传）")
    skill_attr: str | None = Field(None, description="技能属性名（base 模式必传）")
    attacker_attrs: list[str] = Field(default_factory=list, description="进攻方宠物属性列表")
    defender_attrs: list[str] = Field(default_factory=list, description="被进攻方宠物属性列表")

    # 威力固定加值 / 威力数值变化，默认 0
    power_delta: float = Field(0.0, description="威力固定加值（威力数值变化）")
    # 以下加成均传「增减部分」的小数，如 +20% 传 0.2，-40% 传 -0.4，计算时按 1+x
    trait_atk_bonus: float = Field(0.0, description="特性攻击力加成（小数，0.2 表示 +20%）")
    trait_power_bonus: float = Field(0.0, description="特性威力加成（小数）")
    other_atk_bonus: float = Field(0.0, description="其他攻击力加成，如力增（小数）")
    other_power_bonus: float = Field(0.0, description="其他威力加成（小数）")
    defender_def_bonus: float = Field(0.0, description="被进攻方防御加成（小数），1+x 作双防加成")


class DamageCalcResponse(BaseModel):
    damage: int  # 最终伤害（含连击）
    per_hit_damage: int  # 单次伤害（四舍五入后）
    combo_count: int
    power: float  # 参与计算的威力（保留两位小数）
    attack: int  # 实际使用的攻击值
    defense: int  # 实际使用的防御值
    type_coef: float  # 克制系数
    stab: bool  # 是否触发本系加成
