export interface Banner {
  id: number
  title: string
  image_url: string
  link_type: string
  link_param: string
  link_extra: string
  sort_order: number
  is_active: boolean
}

export interface LineupMember {
  id: number
  pokemon_id: number | null
  random_pk_dict_id?: number | null
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
