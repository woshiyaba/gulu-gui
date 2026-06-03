import { request } from '@/utils/request'
import type {
  DamageCalcRequest,
  DamageCalcResponse,
  DamageStatRequest,
  DamageStatResponse,
} from '@/types/damage'

/** 计算宠物六维真实属性值。 */
export function calcPokemonStats(payload: DamageStatRequest) {
  return request<DamageStatResponse>({
    url: '/api/damage/stats',
    method: 'POST',
    data: payload,
  })
}

/** 计算技能伤害真实数值（PVP）。 */
export function calcDamage(payload: DamageCalcRequest) {
  return request<DamageCalcResponse>({
    url: '/api/damage/calc',
    method: 'POST',
    data: payload,
  })
}
