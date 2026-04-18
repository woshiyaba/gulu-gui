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
