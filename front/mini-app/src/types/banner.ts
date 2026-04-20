export interface Banner {
  id: number
  title: string
  image_url: string
  link_type: string
  link_param: string
  sort_order: number
  is_active: boolean
}

export interface StarlightDuelPet {
  id: number
  pet_id: number
  pet_name: string
  pet_image: string
  sort_order: number
  skill_1_id: number | null
  skill_1_name: string
  skill_2_id: number | null
  skill_2_name: string
  skill_3_id: number | null
  skill_3_name: string
  skill_4_id: number | null
  skill_4_name: string
}

export interface StarlightDuelEpisode {
  id: number
  episode_number: number
  title: string
  strategy_text: string
  is_active: boolean
  pets: StarlightDuelPet[]
}
