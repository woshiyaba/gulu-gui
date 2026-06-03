// ── 属性计算 (/api/damage/stats) ──────────────────────────

export interface DamageStatItem {
  key: string
  label: string
  base: number
  iv: number
  ev: number
  l: number
  nature_coef: number
  value: number
}

export interface DamageStatResponse {
  level: number
  personality_id: number | null
  personality_name: string
  iv_value: number
  iv_stats: string[]
  hp: DamageStatItem
  atk: DamageStatItem
  matk: DamageStatItem
  def_val: DamageStatItem
  mdef: DamageStatItem
  spd: DamageStatItem
}

export interface DamageStatRequest {
  hp: number
  atk: number
  matk: number
  def_val: number
  mdef: number
  spd: number
  iv_stats?: string[]
  personality_id?: number | null
  personality_name?: string | null
  level?: number
  hp_ev?: number
  atk_ev?: number
  matk_ev?: number
  def_ev?: number
  mdef_ev?: number
  spd_ev?: number
}

// ── 伤害计算 (/api/damage/calc) ───────────────────────────

export interface CombatStats {
  hp?: number
  atk?: number
  matk?: number
  def_val?: number
  mdef?: number
  spd?: number
}

export type PowerMode = 'known' | 'base'
export type SkillCategory = '物攻' | '魔攻'

export interface DamageCalcRequest {
  attacker: CombatStats
  defender: CombatStats
  combo_count?: number
  power_mode: PowerMode
  skill_category: SkillCategory
  /** known 模式：已知威力 */
  power?: number | null
  /** base 模式：技能原威力 */
  skill_base_power?: number | null
  skill_attr?: string | null
  attacker_attrs?: string[]
  defender_attrs?: string[]
  /** 威力固定加值（威力数值变化），默认 0 */
  power_delta?: number
  /** 以下均为小数，0.2 表示 +20% */
  trait_atk_bonus?: number
  trait_power_bonus?: number
  other_atk_bonus?: number
  other_power_bonus?: number
  defender_def_bonus?: number
}

export interface DamageCalcResponse {
  damage: number
  per_hit_damage: number
  combo_count: number
  power: number
  attack: number
  defense: number
  type_coef: number
  stab: boolean
}
