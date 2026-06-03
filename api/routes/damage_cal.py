from fastapi import APIRouter

from api.schemas.damage_cal import (
    DamageCalcRequest,
    DamageCalcResponse,
    DamageStatRequest,
    DamageStatResponse,
)
from api.services import damage_cal_service

router = APIRouter(prefix="/api/damage")


@router.post("/stats", response_model=DamageStatResponse)
async def calc_pokemon_stats(payload: DamageStatRequest):
    """
    计算用户选择宠物的六维真实属性值。

    - L = (种族值 + 个体值/2) / 100，个体值仅勾选的三个属性为 60，其余为 0
    - 生命：((2L + 1) * 等级 + 50L + 10) * 性格系数 + 努力值
    - 其余：(L * 等级 + 50L + 10) * 性格系数 + 努力值
    - 真实值与 L 指标均四舍五入（L 保留两位小数）
    """
    return await damage_cal_service.calc_stats(payload)


@router.post("/calc", response_model=DamageCalcResponse)
async def calc_pokemon_damage(payload: DamageCalcRequest):
    """
    计算技能伤害真实数值（PVP）。

    - 已知威力（power_mode=known）：直接按
      ((威力 * 攻击 * 37/41) / 防御) * 连击次数
    - 基础威力（power_mode=base）：先按公式推导威力
      威力 =（技能原威力 + 威力数值变化）* 本系加成(1.25) * 攻击力加成 * 威力加成 * 克制系数 / 双防加成
      再按同样的伤害公式计算
    - 技能类别 "物攻" 用物攻/物防，"魔攻" 用魔攻/魔防；单次伤害四舍五入后乘连击次数
    """
    return await damage_cal_service.calc_damage(payload)
