import axios from 'axios'
import type {
  Attribute,
  PokemonBodyMatchResponse,
  PokemonDetail,
  PokemonEvolutionChain,
  PokemonListResponse,
  SkillStoneListResponse,
} from '@/types'

const DEFAULT_API_BASE_URL = import.meta.env.PROD
  ? 'http://101.126.137.23:8000'
  : 'http://localhost:8000'

// 统一收口接口地址，打包和本地开发分别走不同环境配置。
const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/+$/, '')

const http = axios.create({
  baseURL: apiBaseUrl,
  timeout: 10000,
})

export interface PokemonQuery {
  name?: string
  attr?: string[]
  egg_group?: string[]
  order_by?: 'no' | 'total_stats' | 'hp' | 'atk' | 'matk' | 'def_val' | 'mdef' | 'spd'
  order_dir?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export interface PokemonBodyMatchQuery {
  height_m: number
  weight_kg: number
}

export interface SkillStoneQuery {
  skill_name?: string
}

export function fetchAttributes(): Promise<Attribute[]> {
  return http.get<Attribute[]>('/api/attributes').then((r) => r.data)
}

export function fetchEggGroups(): Promise<string[]> {
  return http.get<string[]>('/api/egg-groups').then((r) => r.data)
}

export function fetchPokemon(query: PokemonQuery = {}): Promise<PokemonListResponse> {
  const params = new URLSearchParams()
  if (query.name) params.append('name', query.name)
  if (query.page !== undefined) params.append('page', String(query.page))
  if (query.page_size !== undefined) params.append('page_size', String(query.page_size))
  if (query.order_by) params.append('order_by', query.order_by)
  if (query.order_dir) params.append('order_dir', query.order_dir)
  for (const attr of query.attr || []) {
    params.append('attr', attr)
  }
  for (const group of query.egg_group || []) {
    params.append('egg_group', group)
  }
  return http.get<PokemonListResponse>('/api/pokemon', { params }).then((r) => r.data)
}

export function fetchPokemonDetail(name: string): Promise<PokemonDetail> {
  return http.get<PokemonDetail>(`/api/pokemon/${encodeURIComponent(name)}`).then((r) => r.data)
}

export function fetchPokemonEvolutionChain(name: string): Promise<PokemonEvolutionChain> {
  return http
    .get<PokemonEvolutionChain>(`/api/pokemon/evolution-chain/${encodeURIComponent(name)}`)
    .then((r) => r.data)
}

export function fetchPokemonBodyMatch(
  query: PokemonBodyMatchQuery,
): Promise<PokemonBodyMatchResponse> {
  return http.get<PokemonBodyMatchResponse>('/api/pokemon/body-match', { params: query }).then((r) => r.data)
}

export function fetchSkillStones(query: SkillStoneQuery = {}): Promise<SkillStoneListResponse> {
  const skillName = query.skill_name?.trim()
  const params = skillName ? { skill_name: skillName } : undefined
  return http.get<SkillStoneListResponse>('/api/skill-stones', { params }).then((r) => r.data)
}
