import axios from 'axios'

const DEFAULT_API_BASE_URL = import.meta.env.PROD
  ? 'http://101.126.137.23:8000'
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

const http = axios.create({
  baseURL: apiBaseUrl,
  timeout: 10000,
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
  keyword?: string
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
