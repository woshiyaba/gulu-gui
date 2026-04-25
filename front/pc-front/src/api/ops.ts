import axios from 'axios'

const DEFAULT_API_BASE_URL = import.meta.env.PROD
  ? 'https://wikiroco.com'
  : 'http://localhost:8000'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/+$/, '')

const TOKEN_KEY = 'ops_access_token'
export const OPS_TOAST_EVENT = 'ops:toast'

export interface OpsUser {
  id: number
  username: string
  nickname: string
  role: 'editor' | 'admin'
}

export interface OpsLoginResponse {
  access_token: string
  token_type: string
  user: OpsUser
}

export interface OpsProfileUpdatePayload {
  nickname: string
  current_password?: string
  new_password?: string
}

export interface OpsDictItem {
  id: number
  dict_type: string
  code: string
  label: string
  extra: string
  sort_order: number
}

export interface OpsDictListResponse {
  total: number
  page: number
  page_size: number
  items: OpsDictItem[]
}

export interface OpsDictPayload {
  dict_type: string
  code: string
  label: string
  extra: string
  sort_order: number
}

export interface OpsUserListResponse {
  items: OpsUser[]
}

export interface OpsUserCreatePayload {
  username: string
  nickname: string
  password: string
  role: 'editor' | 'admin'
}

export interface OpsUserUpdatePayload {
  nickname: string
  password?: string
  role: 'editor' | 'admin'
}

export interface OpsPokemonSkillItem {
  skill_id: number
  type: string
  sort_order: number
}

export interface OpsPokemonItem {
  id: number
  no: string
  name: string
  type_name: string
  form_name: string
  trait_name: string
  attributes: string[]
  egg_groups: string[]
}

export interface OpsPokemonListResponse {
  total: number
  page: number
  page_size: number
  items: OpsPokemonItem[]
}

export interface OpsPokemonDetail {
  id: number
  no: string
  name: string
  image: string
  type: string
  type_name: string
  form: string
  form_name: string
  egg_group: string
  trait_id: number
  detail_url: string
  image_lc: string
  image_yise: string
  chain_id: number | null
  hp: number
  atk: number
  matk: number
  def_val: number
  mdef: number
  spd: number
  total_race: number
  obtain_method: string
  attribute_ids: number[]
  egg_groups: string[]
  skills: OpsPokemonSkillItem[]
}

export interface OpsPokemonOptionItem {
  id: number
  name: string
  icon?: string
}

export interface OpsEvolutionChainStep {
  sort_order: number
  pokemon_name: string
  evolution_condition: string
  image_url?: string
  matched?: boolean
}

export interface OpsEvolutionChain {
  chain_id: number | null
  steps: OpsEvolutionChainStep[]
}

export interface OpsEvolutionGraphNode {
  pokemon_id: number
  pokemon_name: string
  image_url?: string
  is_root?: boolean
}

export interface OpsEvolutionGraphEdge {
  pre_pokemon_id: number
  pokemon_id: number
  pre_evolution_condition: string
}

export interface OpsEvolutionGraph {
  chain_id: number | null
  nodes: OpsEvolutionGraphNode[]
  edges: OpsEvolutionGraphEdge[]
}

export interface OpsPokemonOptionsResponse {
  attributes: OpsPokemonOptionItem[]
  traits: OpsPokemonOptionItem[]
  skills: OpsPokemonOptionItem[]
  skill_sources: string[]
}

export interface OpsFriendImageUploadResponse {
  image_lc: string
  preview_url: string
}

export interface OpsYiseImageUploadResponse {
  image_yise: string
  preview_url: string
}

export interface OpsPokemonUpsertPayload {
  no: string
  name: string
  image: string
  type: string
  type_name: string
  form: string
  form_name: string
  egg_group: string
  trait_id: number
  detail_url: string
  image_lc: string
  image_yise: string
  chain_id: number | null
  hp: number
  atk: number
  matk: number
  def_val: number
  mdef: number
  spd: number
  total_race: number
  obtain_method: string
  attribute_ids: number[]
  egg_groups: string[]
  skills: OpsPokemonSkillItem[]
}

export interface OpsPokemonMarkItem {
  id: number
  key: string
  zh_name: string
  zh_description: string
  sort_order: number
  image: string
  image_url: string
}

export interface OpsPokemonMarkListResponse {
  total: number
  page: number
  page_size: number
  items: OpsPokemonMarkItem[]
}

export interface OpsPokemonMarkPayload {
  key: string
  zh_name: string
  zh_description: string
  sort_order: number
  image: string
}

const http = axios.create({
  baseURL: apiBaseUrl,
  timeout: 10000,
})

const httpUpload = axios.create({
  baseURL: apiBaseUrl,
  timeout: 120000,
})
httpUpload.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export function saveOpsToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearOpsToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function getOpsToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function showOpsToast(message: string, type: 'success' | 'error' | 'info' = 'success') {
  window.dispatchEvent(new CustomEvent(OPS_TOAST_EVENT, { detail: { message, type } }))
}

export function loginOps(username: string, password: string): Promise<OpsLoginResponse> {
  return http.post<OpsLoginResponse>('/api/ops/auth/login', { username, password }).then((r) => r.data)
}

export function fetchOpsMe(): Promise<OpsUser> {
  return http.get<OpsUser>('/api/ops/auth/me').then((r) => r.data)
}

export function updateOpsMe(payload: OpsProfileUpdatePayload): Promise<OpsUser> {
  return http.put<OpsUser>('/api/ops/auth/me', payload).then((r) => r.data)
}

export function fetchOpsDicts(params: {
  dict_type?: string
  code?: string
  label?: string
  page?: number
  page_size?: number
} = {}): Promise<OpsDictListResponse> {
  return http.get<OpsDictListResponse>('/api/ops/dicts', { params }).then((r) => r.data)
}

export function createOpsDict(payload: OpsDictPayload): Promise<OpsDictItem> {
  return http.post<OpsDictItem>('/api/ops/dicts', payload).then((r) => r.data)
}

export function updateOpsDict(id: number, payload: OpsDictPayload): Promise<OpsDictItem> {
  return http.put<OpsDictItem>(`/api/ops/dicts/${id}`, payload).then((r) => r.data)
}

export function deleteOpsDict(id: number): Promise<void> {
  return http.delete(`/api/ops/dicts/${id}`).then(() => undefined)
}

export function fetchOpsUsers(): Promise<OpsUserListResponse> {
  return http.get<OpsUserListResponse>('/api/ops/users').then((r) => r.data)
}

export function createOpsUser(payload: OpsUserCreatePayload): Promise<OpsUser> {
  return http.post<OpsUser>('/api/ops/users', payload).then((r) => r.data)
}

export function updateOpsUser(id: number, payload: OpsUserUpdatePayload): Promise<OpsUser> {
  return http.put<OpsUser>(`/api/ops/users/${id}`, payload).then((r) => r.data)
}

export function deleteOpsUser(id: number): Promise<void> {
  return http.delete(`/api/ops/users/${id}`).then(() => undefined)
}

export function fetchOpsPokemon(params: {
  keyword?: string
  no?: string
  name?: string
  attr_id?: number
  egg_group?: string
  type_code?: string
  form_code?: string
  trait_id?: number
  page?: number
  page_size?: number
} = {}): Promise<OpsPokemonListResponse> {
  return http.get<OpsPokemonListResponse>('/api/ops/pokemon', { params }).then((r) => r.data)
}

export function fetchOpsPokemonDetail(id: number): Promise<OpsPokemonDetail> {
  return http.get<OpsPokemonDetail>(`/api/ops/pokemon/${id}`).then((r) => r.data)
}

export function fetchOpsPokemonOptions(): Promise<OpsPokemonOptionsResponse> {
  return http.get<OpsPokemonOptionsResponse>('/api/ops/pokemon/options').then((r) => r.data)
}

export function uploadOpsFriendImage(file: File): Promise<OpsFriendImageUploadResponse> {
  const body = new FormData()
  body.append('file', file)
  return httpUpload
    .post<OpsFriendImageUploadResponse>('/api/ops/pokemon/friend-image', body)
    .then((r) => r.data)
}

export function uploadOpsYiseImage(file: File): Promise<OpsYiseImageUploadResponse> {
  const body = new FormData()
  body.append('file', file)
  return httpUpload
    .post<OpsYiseImageUploadResponse>('/api/ops/pokemon/yise-image', body)
    .then((r) => r.data)
}

export function createOpsPokemon(payload: OpsPokemonUpsertPayload): Promise<OpsPokemonDetail> {
  return http.post<OpsPokemonDetail>('/api/ops/pokemon', payload).then((r) => r.data)
}

export function updateOpsPokemon(id: number, payload: OpsPokemonUpsertPayload): Promise<OpsPokemonDetail> {
  return http.put<OpsPokemonDetail>(`/api/ops/pokemon/${id}`, payload).then((r) => r.data)
}

export function deleteOpsPokemon(id: number): Promise<void> {
  return http.delete(`/api/ops/pokemon/${id}`).then(() => undefined)
}

export function fetchOpsPokemonEvolutionChain(id: number): Promise<OpsEvolutionChain> {
  return http.get<OpsEvolutionChain>(`/api/ops/pokemon/${id}/evolution-chain`).then((r) => r.data)
}

export function updateOpsPokemonEvolutionChain(id: number, steps: OpsEvolutionChainStep[]): Promise<OpsEvolutionChain> {
  return http.put<OpsEvolutionChain>(`/api/ops/pokemon/${id}/evolution-chain`, { steps }).then((r) => r.data)
}

export function searchOpsPokemonEvolutionChain(keyword: string): Promise<OpsEvolutionChain> {
  return http.get<OpsEvolutionChain>('/api/ops/pokemon/evolution-chain/search', { params: { keyword } }).then((r) => r.data)
}

export function fetchOpsEvolutionGraphByChainId(chainId: number): Promise<OpsEvolutionGraph> {
  return http.get<OpsEvolutionGraph>(`/api/ops/evolution-chains/${chainId}`).then((r) => r.data)
}

export function fetchOpsEvolutionGraphByPokemonId(pokemonId: number): Promise<OpsEvolutionGraph> {
  return http.get<OpsEvolutionGraph>(`/api/ops/evolution-chains/by-pokemon/${pokemonId}`).then((r) => r.data)
}

export function updateOpsEvolutionGraphByPokemonId(
  pokemonId: number,
  payload: { nodes: Array<{ pokemon_id: number }>; edges: OpsEvolutionGraphEdge[] },
): Promise<OpsEvolutionGraph> {
  return http.put<OpsEvolutionGraph>(`/api/ops/evolution-chains/by-pokemon/${pokemonId}`, payload).then((r) => r.data)
}

export function deleteOpsEvolutionGraphByChainId(chainId: number): Promise<void> {
  return http.delete(`/api/ops/evolution-chains/${chainId}`).then(() => undefined)
}

// ---------- 技能维护 ----------

export interface OpsSkillItem {
  id: number
  name: string
  attr: string
  type: string
  power: number
  consume: number
  skill_desc: string
  icon: string
  icon_url: string
}

export interface OpsSkillListResponse {
  total: number
  page: number
  page_size: number
  items: OpsSkillItem[]
}

export interface OpsSkillUpsertPayload {
  name: string
  attr: string
  type: string
  power: number
  consume: number
  skill_desc: string
  icon: string
}

export interface OpsSkillUsageItem {
  id: number
  no: string
  name: string
  type: string
  sort_order: number
}

export interface OpsSkillUsageResponse {
  total: number
  items: OpsSkillUsageItem[]
}

export interface OpsSkillOptionsResponse {
  attrs: string[]
  types: string[]
}

export interface OpsSkillIconUploadResponse {
  icon: string
  preview_url: string
}

export function fetchOpsSkills(params: {
  keyword?: string
  attr?: string
  type?: string
  page?: number
  page_size?: number
} = {}): Promise<OpsSkillListResponse> {
  return http.get<OpsSkillListResponse>('/api/ops/skills', { params }).then((r) => r.data)
}

export function fetchOpsSkillDetail(id: number): Promise<OpsSkillItem> {
  return http.get<OpsSkillItem>(`/api/ops/skills/${id}`).then((r) => r.data)
}

export function fetchOpsSkillOptions(): Promise<OpsSkillOptionsResponse> {
  return http.get<OpsSkillOptionsResponse>('/api/ops/skills/options').then((r) => r.data)
}

export function fetchOpsSkillUsages(id: number): Promise<OpsSkillUsageResponse> {
  return http.get<OpsSkillUsageResponse>(`/api/ops/skills/${id}/usages`).then((r) => r.data)
}

export function createOpsSkill(payload: OpsSkillUpsertPayload): Promise<OpsSkillItem> {
  return http.post<OpsSkillItem>('/api/ops/skills', payload).then((r) => r.data)
}

export function updateOpsSkill(id: number, payload: OpsSkillUpsertPayload): Promise<OpsSkillItem> {
  return http.put<OpsSkillItem>(`/api/ops/skills/${id}`, payload).then((r) => r.data)
}

export function deleteOpsSkill(id: number, force = false): Promise<void> {
  return http.delete(`/api/ops/skills/${id}`, { params: force ? { force: 1 } : {} }).then(() => undefined)
}

export function uploadOpsSkillIcon(file: File): Promise<OpsSkillIconUploadResponse> {
  const body = new FormData()
  body.append('file', file)
  return httpUpload
    .post<OpsSkillIconUploadResponse>('/api/ops/skills/icon', body)
    .then((r) => r.data)
}

// ---------- 技能石维护 ----------

export interface OpsSkillStoneItem {
  id: number
  skill_id: number
  skill_name: string
  skill_attr: string
  skill_type: string
  skill_icon: string
  skill_icon_url: string
  obtain_method: string
}

export interface OpsSkillStoneListResponse {
  total: number
  page: number
  page_size: number
  items: OpsSkillStoneItem[]
}

export interface OpsSkillStoneCreatePayload {
  skill_id: number
  obtain_method: string
}

export interface OpsSkillStoneUpdatePayload {
  obtain_method: string
}

export interface OpsSkillStoneAvailableSkill {
  id: number
  name: string
  attr: string
  type: string
  icon: string
  icon_url: string
}

export interface OpsSkillStoneAvailableResponse {
  items: OpsSkillStoneAvailableSkill[]
}

export function fetchOpsSkillStones(params: {
  keyword?: string
  attr?: string
  type?: string
  obtain_keyword?: string
  page?: number
  page_size?: number
} = {}): Promise<OpsSkillStoneListResponse> {
  return http.get<OpsSkillStoneListResponse>('/api/ops/skill-stones', { params }).then((r) => r.data)
}

export function fetchOpsSkillStoneDetail(id: number): Promise<OpsSkillStoneItem> {
  return http.get<OpsSkillStoneItem>(`/api/ops/skill-stones/${id}`).then((r) => r.data)
}

export function fetchOpsSkillStoneAvailableSkills(params: {
  keyword?: string
  limit?: number
} = {}): Promise<OpsSkillStoneAvailableResponse> {
  return http
    .get<OpsSkillStoneAvailableResponse>('/api/ops/skill-stones/available-skills', { params })
    .then((r) => r.data)
}

export function createOpsSkillStone(payload: OpsSkillStoneCreatePayload): Promise<OpsSkillStoneItem> {
  return http.post<OpsSkillStoneItem>('/api/ops/skill-stones', payload).then((r) => r.data)
}

export function updateOpsSkillStone(id: number, payload: OpsSkillStoneUpdatePayload): Promise<OpsSkillStoneItem> {
  return http.put<OpsSkillStoneItem>(`/api/ops/skill-stones/${id}`, payload).then((r) => r.data)
}

export function deleteOpsSkillStone(id: number): Promise<void> {
  return http.delete(`/api/ops/skill-stones/${id}`).then(() => undefined)
}

// ── Banner ──────────────────────────────────────────────

export interface OpsBannerItem {
  id: number
  title: string
  image_url: string
  link_type: string
  link_param: string
  link_extra: string
  sort_order: number
  is_active: boolean
}

export interface OpsBannerListResponse {
  total: number
  page: number
  page_size: number
  items: OpsBannerItem[]
}

export interface OpsBannerPayload {
  title: string
  image_url: string
  link_type: string
  link_param: string
  sort_order: number
  is_active: boolean
}

export function fetchOpsBanners(params: { page?: number; page_size?: number } = {}): Promise<OpsBannerListResponse> {
  return http.get<OpsBannerListResponse>('/api/ops/banners', { params }).then((r) => r.data)
}

export function createOpsBanner(payload: OpsBannerPayload): Promise<OpsBannerItem> {
  return http.post<OpsBannerItem>('/api/ops/banners', payload).then((r) => r.data)
}

export function updateOpsBanner(id: number, payload: OpsBannerPayload): Promise<OpsBannerItem> {
  return http.put<OpsBannerItem>(`/api/ops/banners/${id}`, payload).then((r) => r.data)
}

export function deleteOpsBanner(id: number): Promise<void> {
  return http.delete(`/api/ops/banners/${id}`).then(() => undefined)
}

// ── 精灵性格 ────────────────────────────────────────────

export type OpsPersonalityStat = 'hp' | 'phy_atk' | 'mag_atk' | 'phy_def' | 'mag_def' | 'spd'

export interface OpsPersonalityItem {
  id: number
  name: string
  hp_mod_pct: number
  phy_atk_mod_pct: number
  mag_atk_mod_pct: number
  phy_def_mod_pct: number
  mag_def_mod_pct: number
  spd_mod_pct: number
  buff_stat: OpsPersonalityStat | null
  nerf_stat: OpsPersonalityStat | null
  is_neutral: boolean
}

export interface OpsPersonalityListResponse {
  total: number
  page: number
  page_size: number
  items: OpsPersonalityItem[]
}

export interface OpsPersonalityUpsertPayload {
  id?: number | null
  name: string
  hp_mod_pct: number
  phy_atk_mod_pct: number
  mag_atk_mod_pct: number
  phy_def_mod_pct: number
  mag_def_mod_pct: number
  spd_mod_pct: number
}

export interface OpsPersonalityResetResponse {
  inserted: number
  source: string
}

export function fetchOpsPersonalities(params: {
  keyword?: string
  buff_stat?: string
  nerf_stat?: string
  page?: number
  page_size?: number
} = {}): Promise<OpsPersonalityListResponse> {
  return http.get<OpsPersonalityListResponse>('/api/ops/personalities', { params }).then((r) => r.data)
}

export function fetchOpsPersonalityDetail(id: number): Promise<OpsPersonalityItem> {
  return http.get<OpsPersonalityItem>(`/api/ops/personalities/${id}`).then((r) => r.data)
}

export function createOpsPersonality(payload: OpsPersonalityUpsertPayload): Promise<OpsPersonalityItem> {
  return http.post<OpsPersonalityItem>('/api/ops/personalities', payload).then((r) => r.data)
}

export function updateOpsPersonality(id: number, payload: OpsPersonalityUpsertPayload): Promise<OpsPersonalityItem> {
  return http.put<OpsPersonalityItem>(`/api/ops/personalities/${id}`, payload).then((r) => r.data)
}

export function deleteOpsPersonality(id: number): Promise<void> {
  return http.delete(`/api/ops/personalities/${id}`).then(() => undefined)
}

export function resetOpsPersonalities(): Promise<OpsPersonalityResetResponse> {
  return http.post<OpsPersonalityResetResponse>('/api/ops/personalities/reset').then((r) => r.data)
}

// ── 精灵阵容 ────────────────────────────────────────────

export type OpsPokemonLineupStatKey = string

export interface OpsPokemonLineupMember {
  id?: number
  pokemon_id: number
  pokemon_name: string
  pokemon_image: string
  sort_order: number
  bloodline_dict_id: number | null
  bloodline_label: string
  personality_id: number | null
  personality_name_zh: string
  qual_1: OpsPokemonLineupStatKey | ''
  qual_2: OpsPokemonLineupStatKey | ''
  qual_3: OpsPokemonLineupStatKey | ''
  skill_1_id: number | null
  skill_1_name: string
  skill_1_image?: string
  skill_2_id: number | null
  skill_2_name: string
  skill_2_image?: string
  skill_3_id: number | null
  skill_3_name: string
  skill_3_image?: string
  skill_4_id: number | null
  skill_4_name: string
  skill_4_image?: string
  member_desc: string
}

export interface OpsPokemonLineup {
  id: number
  title: string
  lineup_desc: string
  source_type: string
  resonance_magic_id: number | null
  resonance_magic_name: string
  resonance_magic_icon?: string
  sort_order: number
  is_active: boolean
  members: OpsPokemonLineupMember[]
}

export interface OpsPokemonLineupListItem {
  id: number
  title: string
  source_type: string
  resonance_magic_id: number | null
  resonance_magic_name: string
  resonance_magic_icon?: string
  sort_order: number
  is_active: boolean
  member_count: number
}

export interface OpsPokemonLineupListResponse {
  total: number
  page: number
  page_size: number
  items: OpsPokemonLineupListItem[]
}

export interface OpsPokemonLineupMemberPayload {
  pokemon_id: number
  sort_order: number
  bloodline_dict_id: number | null
  personality_id: number | null
  qual_1: OpsPokemonLineupStatKey | ''
  qual_2: OpsPokemonLineupStatKey | ''
  qual_3: OpsPokemonLineupStatKey | ''
  skill_1_id: number | null
  skill_2_id: number | null
  skill_3_id: number | null
  skill_4_id: number | null
  member_desc: string
}

export interface OpsPokemonLineupPayload {
  title: string
  lineup_desc: string
  source_type: string
  resonance_magic_id: number | null
  sort_order: number
  is_active: boolean
  members: OpsPokemonLineupMemberPayload[]
}

export interface OpsPokemonLineupSearchItem {
  id: number
  name: string
  image?: string
}

export interface OpsPokemonLineupSearchResponse {
  items: OpsPokemonLineupSearchItem[]
}

export function searchPokemonLineupPokemon(keyword: string): Promise<OpsPokemonLineupSearchResponse> {
  return http.get<OpsPokemonLineupSearchResponse>('/api/ops/pokemon-lineups/search-pokemon', { params: { keyword } }).then((r) => r.data)
}

export function searchPokemonLineupSkills(params: {
  keyword: string
  pokemon_id: number
  exclude_skill_ids?: number[]
}): Promise<OpsPokemonLineupSearchResponse> {
  const query = new URLSearchParams()
  query.append('keyword', params.keyword)
  query.append('pokemon_id', String(params.pokemon_id))
  for (const id of params.exclude_skill_ids ?? []) {
    query.append('exclude_skill_ids', String(id))
  }
  return http
    .get<OpsPokemonLineupSearchResponse>('/api/ops/pokemon-lineups/search-skills', { params: query })
    .then((r) => r.data)
}

export function fetchOpsPokemonLineups(params: {
  keyword?: string
  source_type?: string
  is_active?: boolean | null
  page?: number
  page_size?: number
} = {}): Promise<OpsPokemonLineupListResponse> {
  return http.get<OpsPokemonLineupListResponse>('/api/ops/pokemon-lineups', { params }).then((r) => r.data)
}

export function fetchOpsPokemonLineup(id: number): Promise<OpsPokemonLineup> {
  return http.get<OpsPokemonLineup>(`/api/ops/pokemon-lineups/${id}`).then((r) => r.data)
}

export function createOpsPokemonLineup(payload: OpsPokemonLineupPayload): Promise<OpsPokemonLineup> {
  return http.post<OpsPokemonLineup>('/api/ops/pokemon-lineups', payload).then((r) => r.data)
}

export function updateOpsPokemonLineup(id: number, payload: OpsPokemonLineupPayload): Promise<OpsPokemonLineup> {
  return http.put<OpsPokemonLineup>(`/api/ops/pokemon-lineups/${id}`, payload).then((r) => r.data)
}

export function deleteOpsPokemonLineup(id: number): Promise<void> {
  return http.delete(`/api/ops/pokemon-lineups/${id}`).then(() => undefined)
}

// ── 共鸣魔法 ────────────────────────────────────────────

export interface OpsResonanceMagicItem {
  id: number
  name: string
  description: string
  max_usage_count: number
  icon: string
  icon_url?: string
  sort_order: number
}

export interface OpsResonanceMagicListResponse {
  total: number
  page: number
  page_size: number
  items: OpsResonanceMagicItem[]
}

export interface OpsResonanceMagicPayload {
  name: string
  description: string
  max_usage_count: number
  icon: string
  sort_order: number
}

export interface OpsResonanceMagicIconUploadResponse {
  icon: string
  preview_url: string
}

export function fetchOpsResonanceMagics(params: {
  keyword?: string
  page?: number
  page_size?: number
} = {}): Promise<OpsResonanceMagicListResponse> {
  return http.get<OpsResonanceMagicListResponse>('/api/ops/resonance-magics', { params }).then((r) => r.data)
}

export function createOpsResonanceMagic(payload: OpsResonanceMagicPayload): Promise<OpsResonanceMagicItem> {
  return http.post<OpsResonanceMagicItem>('/api/ops/resonance-magics', payload).then((r) => r.data)
}

export function updateOpsResonanceMagic(id: number, payload: OpsResonanceMagicPayload): Promise<OpsResonanceMagicItem> {
  return http.put<OpsResonanceMagicItem>(`/api/ops/resonance-magics/${id}`, payload).then((r) => r.data)
}

export function deleteOpsResonanceMagic(id: number): Promise<void> {
  return http.delete(`/api/ops/resonance-magics/${id}`).then(() => undefined)
}

export function uploadOpsResonanceMagicIcon(file: File): Promise<OpsResonanceMagicIconUploadResponse> {
  const body = new FormData()
  body.append('file', file)
  return httpUpload
    .post<OpsResonanceMagicIconUploadResponse>('/api/ops/resonance-magics/icon', body)
    .then((r) => r.data)
}

// ── 名词解释（pokemon-marks） ────────────────────────────

export function fetchOpsPokemonMarks(params: {
  keyword?: string
  page?: number
  page_size?: number
} = {}): Promise<OpsPokemonMarkListResponse> {
  return http.get<OpsPokemonMarkListResponse>('/api/ops/pokemon-marks', { params }).then((r) => r.data)
}

export function createOpsPokemonMark(payload: OpsPokemonMarkPayload): Promise<OpsPokemonMarkItem> {
  return http.post<OpsPokemonMarkItem>('/api/ops/pokemon-marks', payload).then((r) => r.data)
}

export function updateOpsPokemonMark(id: number, payload: OpsPokemonMarkPayload): Promise<OpsPokemonMarkItem> {
  return http.put<OpsPokemonMarkItem>(`/api/ops/pokemon-marks/${id}`, payload).then((r) => r.data)
}

export function deleteOpsPokemonMark(id: number): Promise<void> {
  return http.delete(`/api/ops/pokemon-marks/${id}`).then(() => undefined)
}

// ── 印记维护（marks） ────────────────────────────────────

export interface OpsMarkItem {
  id: number
  key: string
  zh_name: string
  zh_description: string
  image: string
  sort_order: number
}

export interface OpsMarkListResponse {
  total: number
  page: number
  page_size: number
  items: OpsMarkItem[]
}

export interface OpsMarkPayload {
  key: string
  zh_name: string
  zh_description: string
  image: string
  sort_order: number
}

export function fetchOpsMarks(params: {
  keyword?: string
  page?: number
  page_size?: number
} = {}): Promise<OpsMarkListResponse> {
  return http.get<OpsMarkListResponse>('/api/ops/marks', { params }).then((r) => r.data)
}

export function createOpsMark(payload: OpsMarkPayload): Promise<OpsMarkItem> {
  return http.post<OpsMarkItem>('/api/ops/marks', payload).then((r) => r.data)
}

export function updateOpsMark(id: number, payload: OpsMarkPayload): Promise<OpsMarkItem> {
  return http.put<OpsMarkItem>(`/api/ops/marks/${id}`, payload).then((r) => r.data)
}

export function deleteOpsMark(id: number): Promise<void> {
  return http.delete(`/api/ops/marks/${id}`).then(() => undefined)
}
