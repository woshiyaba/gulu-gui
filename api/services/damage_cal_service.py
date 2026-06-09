import math
import time
from fractions import Fraction

from fastapi import HTTPException

from api.repositories import attribute_matchup_repository
from api.schemas.damage_cal import (
    STAT_KEYS,
    STAT_LABELS,
    STAT_TO_PERSONALITY_COL,
    DamageCalcRequest,
    DamageCalcResponse,
    DamageStatItem,
    DamageStatRequest,
    DamageStatResponse,
)
from api.services import personality_service
from api.utils.rounding import round_half_up
from api.utils.type_chart import combine_defensive_multipliers

# 勾选属性额外获得的个体值，固定为 60
IV_VALUE = 60
# 个体值勾选数量上限
IV_MAX_COUNT = 3
# 本系技能加成
STAB_MULTIPLIER = 1.25
# 伤害公式固定系数 37/41
DAMAGE_FACTOR = 37 / 41

# ── 性格列表内存缓存（1 小时刷新一次） ──────────────────────────
_PERSONALITY_CACHE_TTL = 3600  # 秒
_personality_cache: dict = {"data": None, "ts": 0.0}


async def _get_personalities() -> list[dict]:
    """获取性格列表，命中缓存则直接返回，超过 TTL 后重新查询。"""
    now = time.monotonic()
    if (
        _personality_cache["data"] is not None
        and now - _personality_cache["ts"] < _PERSONALITY_CACHE_TTL
    ):
        return _personality_cache["data"]
    data = await personality_service.list_personalities_public()
    _personality_cache["data"] = data
    _personality_cache["ts"] = now
    return data


async def _resolve_personality(
    personality_id: int | None, personality_name: str | None
) -> dict | None:
    """根据 id 或名称从缓存中解析性格；都未传则返回 None（中性，系数全为 1）。"""
    if personality_id is None and not personality_name:
        return None
    personalities = await _get_personalities()
    if personality_id is not None:
        for p in personalities:
            if p.get("id") == personality_id:
                return p
    if personality_name:
        name = personality_name.strip()
        for p in personalities:
            if (p.get("name") or "").strip() == name:
                return p
    raise HTTPException(status_code=404, detail="性格不存在")


def _nature_coef(personality: dict | None, stat_key: str) -> float:
    """性格系数：1 + 该属性的修正百分比；中性 / 无修正则为 1。"""
    if not personality:
        return 1.0
    col = STAT_TO_PERSONALITY_COL[stat_key]
    return 1.0 + float(personality.get(col) or 0.0)


# ── 属性计算 ────────────────────────────────────────────────

async def calc_stats(payload: DamageStatRequest) -> DamageStatResponse:
    """根据种族值、个体值勾选、性格、努力值计算六维真实属性值。"""
    iv_stats = list(dict.fromkeys(payload.iv_stats))  # 去重保序
    invalid = [s for s in iv_stats if s not in STAT_KEYS]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"无效的属性键：{', '.join(invalid)}；可选值：{', '.join(STAT_KEYS)}",
        )
    if len(iv_stats) > IV_MAX_COUNT:
        raise HTTPException(status_code=400, detail=f"最多勾选 {IV_MAX_COUNT} 个属性获得个体值")

    personality = await _resolve_personality(payload.personality_id, payload.personality_name)
    level = payload.level

    base_values = {
        "hp": payload.hp,
        "atk": payload.atk,
        "matk": payload.matk,
        "def_val": payload.def_val,
        "mdef": payload.mdef,
        "spd": payload.spd,
    }
    ev_values = {
        "hp": payload.hp_ev,
        "atk": payload.atk_ev,
        "matk": payload.matk_ev,
        "def_val": payload.def_ev,
        "mdef": payload.mdef_ev,
        "spd": payload.spd_ev,
    }

    items: dict[str, DamageStatItem] = {}
    for key in STAT_KEYS:
        base = base_values[key]
        iv = IV_VALUE if key in iv_stats else 0
        ev = ev_values[key]
        coef = _nature_coef(personality, key)

        l = (base + iv / 2) / 100
        if key == "hp":
            raw = ((2 * l + 1) * level + 50 * l + 10) * coef + ev
        else:
            raw = (l * level + 50 * l + 10) * coef + ev

        items[key] = DamageStatItem(
            key=key,
            label=STAT_LABELS[key],
            base=base,
            iv=iv,
            ev=ev,
            l=round_half_up(l, 2),
            nature_coef=coef,
            value=int(round_half_up(raw)),
        )

    return DamageStatResponse(
        level=level,
        personality_id=personality.get("id") if personality else None,
        personality_name=(personality.get("name") if personality else "") or "",
        iv_value=IV_VALUE,
        iv_stats=iv_stats,
        **items,
    )


# ── 伤害计算 ────────────────────────────────────────────────

async def _type_coefficient(skill_attr: str, defender_attrs: list[str]) -> float:
    """
    计算技能属性对被进攻方（1~2 属性）的克制系数。

    单方倍率：0.5=抵抗，1=正常，2=克制；多属性按洛克王国规则合并
    （双克制为 3 而非 4），合并逻辑复用 combine_defensive_multipliers。、sta
    """
    defenders = list(dict.fromkeys([d for d in defender_attrs if d]))
    if not defenders:
        return 1.0

    rows = await attribute_matchup_repository.list_matchups_for_attackers([skill_attr])
    single: dict[str, Fraction] = {}
    for row in rows:
        d = row.get("defender_attr")
        if d:
            single[d] = Fraction(str(row.get("multiplier")))

    multipliers = [single.get(d, Fraction(1, 1)) for d in defenders]
    return float(combine_defensive_multipliers(multipliers))


def _attack_defense(payload: DamageCalcRequest) -> tuple[int, int]:
    """根据技能类别选取攻击值与防御值。"""
    if payload.skill_category == "魔攻":
        return payload.attacker.matk, payload.defender.mdef
    return payload.attacker.atk, payload.defender.def_val


async def _resolve_power(payload: DamageCalcRequest) -> tuple[float, float, bool]:
    """
    解析参与计算的威力。

    返回 (威力, 克制系数, 是否本系加成)。
    - known 模式：直接使用 payload.power
    - base 模式：按公式
      威力 = (技能原威力 + 威力数值变化) * 本系加成 * 攻击力加成 * 威力加成 * 克制系数 / 双防加成
    """
    if payload.power_mode == "known":
        if payload.power is None:
            raise HTTPException(status_code=400, detail="已知威力模式必须传 power")
        return payload.power, 1.0, False

    # base 模式
    if payload.skill_base_power is None:
        raise HTTPException(status_code=400, detail="基础威力模式必须传 skill_base_power")

    # skill_attr 可选：未传（如手填威力+类型而无技能属性）时，
    # 不触发本系加成，克制系数按 1 处理。
    stab = bool(payload.skill_attr) and payload.skill_attr in payload.attacker_attrs
    stab_mul = STAB_MULTIPLIER if stab else 1.0
    if payload.skill_attr and payload.defender_attrs:
        type_coef = await _type_coefficient(payload.skill_attr, payload.defender_attrs)
    else:
        type_coef = 1.0

    atk_bonus = (1 + payload.trait_atk_bonus) * (1 + payload.other_atk_bonus)
    power_bonus = (1 + payload.trait_power_bonus) * (1 + payload.other_power_bonus)
    def_bonus = 1 + payload.defender_def_bonus
    if def_bonus <= 0:
        raise HTTPException(status_code=400, detail="双防加成不能 <= 0")

    power = (
        (payload.skill_base_power + payload.power_delta)
        * stab_mul
        * atk_bonus
        * power_bonus
        * type_coef
        / def_bonus
    )
    return power, type_coef, stab


async def calc_damage(payload: DamageCalcRequest) -> DamageCalcResponse:
    """计算技能伤害真实数值。"""
    attack, defense = _attack_defense(payload)
    if defense <= 0:
        raise HTTPException(status_code=400, detail="防御值必须大于 0")

    power, type_coef, stab = await _resolve_power(payload)

    numerator = round_half_up(power * attack * DAMAGE_FACTOR)
    per_hit = math.floor(numerator / defense)
    damage = per_hit * payload.combo_count

    return DamageCalcResponse(
        damage=damage,
        per_hit_damage=per_hit,
        combo_count=payload.combo_count,
        power=round_half_up(power, 2),
        attack=attack,
        defense=defense,
        type_coef=type_coef,
        stab=stab,
    )
