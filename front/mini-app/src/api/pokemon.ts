import { request } from '@/utils/request'
import type {
  Attribute,
  BattlePkRandomPokemonOption,
  BattlePkRequest,
  BattlePkResponse,
  BloodlineOption,
  Category,
  ChronologyDetail,
  ChronologyListItem,
  MapPoint,
  PersonalityOption,
  PokemonBodyMatchResponse,
  PokemonDetail,
  PokemonEggListResponse,
  PokemonEvolutionChain,
  PokemonFilterOption,
  PokemonFruitListResponse,
  PokemonListResponse,
  PokemonMark,
  ResonanceMagicOption,
  SkillListResponse,
  SkillStoneListResponse,
} from '@/types/pokemon'

export interface PokemonQuery {
  name?: string
  attr?: string
  filter_code?: string
  shiny_only?: boolean
  order_by?: 'no' | 'total_stats' | 'hp' | 'atk' | 'matk' | 'def_val' | 'mdef' | 'spd'
  order_dir?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export interface PokemonBodyMatchQuery {
  height_m: number
  weight_kg: number
}

export interface SkillQuery {
  name?: string
  skill_type?: string
  attr?: string
}

export interface SkillStoneQuery {
  skill_name?: string
}

export function fetchAttributes() {
  return request<Attribute[]>({
    url: '/api/attributes',
  })
}

export function fetchPokemon(query: PokemonQuery = {}) {
  return request<PokemonListResponse>({
    url: '/api/pokemon',
    data: query,
  })
}

export function fetchPokemonDetail(name: string) {
  return request<PokemonDetail>({
    url: `/api/pokemon/${encodeURIComponent(name)}`,
  })
}

export function fetchPokemonBodyMatch(query: PokemonBodyMatchQuery) {
  return request<PokemonBodyMatchResponse>({
    url: '/api/pokemon/body-match',
    data: query,
  })
}

export function fetchPokemonEvolutionChain(name: string) {
  return request<PokemonEvolutionChain>({
    url: `/api/pokemon/evolution-chain/${encodeURIComponent(name)}`,
  })
}

export function fetchEggGroups() {
  return request<string[]>({
    url: '/api/egg-groups',
  })
}

export function fetchSkillTypes() {
  return request<string[]>({
    url: '/api/skill-types',
  })
}

export function fetchSkills(query: SkillQuery = {}) {
  return request<SkillListResponse>({
    url: '/api/skills',
    data: query,
  })
}

export function fetchSkillStones(query: SkillStoneQuery = {}) {
  return request<SkillStoneListResponse>({
    url: '/api/skill-stones',
    data: query,
  })
}

export function fetchCategories() {
  return request<Category[]>({
    url: '/api/pokemon/categories',
  })
}

export function fetchMapPoints() {
  return request<MapPoint[]>({
    url: '/api/pokemon/map-points',
  })
}

export function fetchPokemonMarks() {
  return request<PokemonMark[]>({
    url: '/api/pokemon-marks',
  })
}

export function fetchPokemonFilterOptions() {
  return request<PokemonFilterOption[]>({
    url: '/api/pokemon-filter-options',
  })
}

export function fetchChronology() {
  return request<ChronologyListItem[]>({
    url: '/api/chronology',
  })
}

export function fetchChronologyDetail(id: number) {
  return request<ChronologyDetail>({
    url: `/api/chronology/${id}`,
  })
}

export interface PokemonEggQuery {
  name?: string
  page?: number
  page_size?: number
}

export function fetchPokemonEggs(query: PokemonEggQuery = {}) {
  return request<PokemonEggListResponse>({
    url: '/api/pokemon-eggs',
    data: query,
  })
}

export interface PokemonFruitQuery {
  name?: string
  page?: number
  page_size?: number
}

export function fetchPokemonFruits(query: PokemonFruitQuery = {}) {
  return request<PokemonFruitListResponse>({
    url: '/api/pokemon-fruits',
    data: query,
  })
}

import type { Banner, Lineup } from '@/types/banner'
import type { Announcement } from '@/types/announcement'

export function fetchBanners() {
  return request<Banner[]>({
    url: '/api/banners',
  })
}

export function fetchAnnouncement() {
  return request<Announcement | null>({
    url: '/api/announcement',
  })
}

export function fetchAbout() {
  return request<{ texts: string[] }>({
    url: '/api/announcement/about',
  })
}

export function fetchLineupDetail(id: number) {
  return request<Lineup>({
    url: `/api/pokemon-lineups/${id}`,
  })
}

export function fetchLineupsByIds(ids: number[]) {
  const params = ids.map((id) => `ids=${id}`).join('&')
  return request<{ items: Lineup[] }>({
    url: `/api/pokemon-lineups?${params}`,
  })
}

export function fetchLineups(sourceType?: string) {
  const query = sourceType ? `?source_type=${encodeURIComponent(sourceType)}` : ''
  return request<{ items: Lineup[] }>({
    url: `/api/pokemon-lineups${query}`,
  })
}

export function fetchPersonalities() {
  return request<PersonalityOption[]>({ url: '/api/personalities' })
}

export function fetchBloodlines() {
  return request<BloodlineOption[]>({ url: '/api/bloodlines' })
}

export function fetchBattlePkRandomPokemonModes() {
  return request<BattlePkRandomPokemonOption[]>({
    url: '/api/battle-pk/random-pokemon-modes',
  })
}

export function fetchResonanceMagics() {
  return request<ResonanceMagicOption[]>({ url: '/api/resonance-magics' })
}

export function submitBattlePk(payload: BattlePkRequest) {
  return request<BattlePkResponse>({
    url: '/api/battle-pk',
    method: 'POST',
    data: payload,
    timeout: 120000,
  })
}

export interface AiPkSubmitRequest extends BattlePkRequest {
  user_id: string
}

export interface AiPkSubmitResponse {
  task_id: string
}

export interface AiPkTaskStatusResponse {
  task_id: string
  user_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | string
  result: BattlePkResponse | null
  error: string
  created_at: string | null
  updated_at: string | null
}

export function submitAiPkBattle(payload: AiPkSubmitRequest) {
  return request<AiPkSubmitResponse>({
    url: '/api/ai-pk/battle-pk',
    method: 'POST',
    data: payload,
    timeout: 30000,
  })
}

export function fetchAiPkTask(taskId: string) {
  return request<AiPkTaskStatusResponse>({
    url: `/api/ai-pk/tasks/${encodeURIComponent(taskId)}`,
    timeout: 30000,
  })
}

export interface MerchantProduct {
  name: string
  icon_url: string
  start_time: number | null
  end_time: number | null
  time_label: string
}

export interface MerchantInfo {
  title: string
  subtitle: string
  start_time: number | null
  end_time: number | null
  product_count: number
  products: MerchantProduct[]
}

export function fetchMerchantInfo() {
  return request<MerchantInfo>({
    url: '/api/third/merchant',
  })
}

export interface PetAvatarResponse {
  pet_id: number
  avatar: string
}

export function fetchPetAvatar(petId: number) {
  return request<PetAvatarResponse>({
    url: `/api/chat/pets/${petId}/avatar`,
  })
}

export interface PetChatEnabledResponse {
  pet_id: number
  enabled: boolean
}

export function fetchPetChatEnabled(petId: number) {
  return request<PetChatEnabledResponse>({
    url: `/api/chat/pets/${petId}/enabled`,
  })
}

export interface PetPromptExtraField {
  code: string
  label: string
  type: 'select' | 'text'
  options: string[]
  value: string
}

export interface PetPromptExtraForm {
  pet_id: number
  fields: PetPromptExtraField[]
}

export interface PetPromptExtraUpdateResponse {
  pet_id: number
  nickname: string
  attributes: Record<string, string>
}

export function fetchPetPromptExtra(petId: number, userId: string) {
  return request<PetPromptExtraForm>({
    url: '/api/chat/pet-prompt-extra',
    data: { pet_id: petId, user_id: userId },
  })
}

export function savePetPromptExtra(payload: {
  user_id: string
  pet_id: number
  values: Record<string, string>
}) {
  return request<PetPromptExtraUpdateResponse>({
    url: '/api/chat/pet-prompt-extra-update',
    method: 'POST',
    data: payload,
  })
}
