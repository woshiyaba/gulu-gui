export interface Attribute {
  attr_name: string
  attr_image: string
}

export interface Pokemon {
  no: string
  name: string
  image_url: string
  image_yise_url: string
  type: string
  type_name: string
  form: string
  form_name: string
  attributes: Attribute[]
  egg_groups: string[]
}

export interface PokemonListResponse {
  total: number
  page: number
  page_size: number
  items: Pokemon[]
}

export interface SkillStone {
  skill_name: string
  obtain_method: string
  icon: string
}

export interface PokemonMark {
  id: number
  key: string
  zh_name: string
  zh_description: string
  sort_order: number
  image: string
}

export interface SkillStoneListResponse {
  total: number
  items: SkillStone[]
}

export interface PokemonBodyMatchItem {
  pet_name: string
  image_url: string
}

export interface PokemonBodyMatchResponse {
  height_m: number
  weight_kg: number
  height_cm: number
  weight_g: number
  total: number
  items: PokemonBodyMatchItem[]
}

export interface EvolutionChainItem {
  name: string
  image_url: string
}

export interface EvolutionChainStage {
  sort_order: number
  next_condition: string
  pre_condition: string
  items: EvolutionChainItem[]
}

export interface PokemonEvolutionChain {
  chain_id: number | null
  stages: EvolutionChainStage[]
}

export interface Stats {
  hp: number
  atk: number
  matk: number
  def_val: number
  mdef: number
  spd: number
}

export interface Trait {
  name: string
  desc: string
}

export interface Restrain {
  strong_against: string[]
  weak_against: string[]
  resist: string[]
  resisted: string[]
}

export interface Skill {
  name: string
  attr: string
  power: number
  type: string
  source: string
  consume: number
  desc: string
  icon: string
}

export interface SkillListResponse {
  total: number
  items: Skill[]
}

export interface Category {
  id: number
  category_id: number
  description: string
  type: string
  category_image_url: string
}

export interface MapPoint {
  id: number
  source_id: number
  map_id: number
  title: string
  latitude: number
  longitude: number
  category_id: number
  category_image_url: string
}

/** 受某一进攻招式属性技能时的伤害倍率（双属性为单方倍率相乘） */
export interface DefensiveTypeChartCell {
  attacker_attr: string
  multiplier: number
  label: string
  /** super | neutral | resist | immune — 用于配色 */
  bucket: string
}

export interface DefensiveTypeChart {
  defender_attrs: string[]
  cells: DefensiveTypeChartCell[]
}

export interface LineupMember {
  id: number
  pokemon_id: number
  pokemon_name: string
  pokemon_image: string
  sort_order: number
  bloodline_dict_id: number | null
  bloodline_label: string
  personality_id: number | null
  personality_name_zh: string
  qual_1: string
  qual_2: string
  qual_3: string
  skill_1_id: number | null
  skill_1_name: string
  skill_1_image: string
  skill_2_id: number | null
  skill_2_name: string
  skill_2_image: string
  skill_3_id: number | null
  skill_3_name: string
  skill_3_image: string
  skill_4_id: number | null
  skill_4_name: string
  skill_4_image: string
  member_desc: string
}

export interface Lineup {
  id: number
  title: string
  lineup_desc: string
  source_type: string
  resonance_magic_id: number | null
  resonance_magic_name: string
  resonance_magic_icon: string
  sort_order: number
  is_active: boolean
  members: LineupMember[]
}

export interface LineupListResponse {
  items: Lineup[]
}

// ── 用户 PK 对战 ──────────────────────────────────────────
export interface BattlePkMember {
  pokemon_id: number | null
  pokemon_name: string
  sort_order: number
  bloodline_dict_id: number | null
  bloodline_label: string
  personality_id: number | null
  personality_name_zh: string
  qual_1: string
  qual_2: string
  qual_3: string
  skill_1_id: number | null
  skill_1_name: string
  skill_2_id: number | null
  skill_2_name: string
  skill_3_id: number | null
  skill_3_name: string
  skill_4_id: number | null
  skill_4_name: string
  member_desc: string
}

export interface BattlePkTeam {
  title: string
  lineup_desc: string
  source_type: string
  resonance_magic_id: number | null
  resonance_magic_name: string
  members: BattlePkMember[]
}

export interface BattlePkRequest {
  team_a: BattlePkTeam
  team_b: BattlePkTeam
}

export interface BattlePkSide {
  summary: string
  advantages: string[]
  weaknesses: string[]
}

export interface BattlePkRound {
  round: number
  desc: string
}

export interface BattlePkVerdict {
  winner: string
  win_rate_a: number
  reason: string
}

export interface BattlePkCompleteness {
  ok: boolean
  missing: string[]
}

export interface BattlePkPlan {
  team_a_order: string[]
  team_a_order_reason: string
  team_b_order: string[]
  team_b_order_reason: string
  skill_matchup: string[]
  ability_impact: string[]
}

export interface BattlePkResponse {
  completeness: BattlePkCompleteness
  plan?: BattlePkPlan
  team_a: BattlePkSide
  team_b: BattlePkSide
  key_rounds: BattlePkRound[]
  turning_points: string[]
  verdict: BattlePkVerdict
  error?: string
  raw?: string
}

export interface PersonalityOption {
  id: number
  name: string
  hp_mod_pct: number
  phy_atk_mod_pct: number
  mag_atk_mod_pct: number
  phy_def_mod_pct: number
  mag_def_mod_pct: number
  spd_mod_pct: number
  buff_stat: string | null
  nerf_stat: string | null
  is_neutral: boolean
}

export interface BloodlineOption {
  id: number
  code: string
  label: string
}

/** sys_dict battle_pk_random_pokemon，阵容 PK 随机精灵下拉 */
export interface BattlePkRandomPokemonOption {
  id: number
  code: string
  label: string
  /** any：纯随机；attr：按系别随机，bloodline_code 对应血脉 */
  kind: string
  bloodline_code: string | null
}

export interface ResonanceMagicOption {
  id: number
  name: string
  description: string
  icon_url: string
  max_usage_count: number
}

export interface PokemonDetail extends Pokemon {
  obtain_method: string
  stats: Stats
  trait: Trait
  restrain: Restrain
  skills: Skill[]
  defensive_type_chart?: DefensiveTypeChart | null
}
