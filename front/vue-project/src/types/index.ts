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
}

export interface PokemonListResponse {
  total: number
  page: number
  page_size: number
  items: Pokemon[]
}

export interface PokemonBodyMatchItem {
  pet_name: string
}

export interface PokemonBodyMatchResponse {
  height_m: number
  weight_kg: number
  height_cm: number
  weight_g: number
  total: number
  items: PokemonBodyMatchItem[]
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

export interface PokemonDetail extends Pokemon {
  obtain_method: string
  stats: Stats
  trait: Trait
  restrain: Restrain
  skills: Skill[]
}
