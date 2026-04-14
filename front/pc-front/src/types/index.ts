export interface Attribute {
  attr_name: string
  attr_image: string
}

export interface Pokemon {
  no: string
  name: string
  image_url: string
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

export interface PokemonDetail extends Pokemon {
  obtain_method: string
  stats: Stats
  trait: Trait
  restrain: Restrain
  skills: Skill[]
  defensive_type_chart?: DefensiveTypeChart | null
}
