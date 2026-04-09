import axios from 'axios'
import type { Attribute, PokemonListResponse, PokemonDetail } from '@/types'

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
  attr?: string
  page?: number
  page_size?: number
}

export function fetchAttributes(): Promise<Attribute[]> {
  return http.get<Attribute[]>('/api/attributes').then((r) => r.data)
}

export function fetchPokemon(query: PokemonQuery = {}): Promise<PokemonListResponse> {
  return http.get<PokemonListResponse>('/api/pokemon', { params: query }).then((r) => r.data)
}

export function fetchPokemonDetail(name: string): Promise<PokemonDetail> {
  return http.get<PokemonDetail>(`/api/pokemon/${encodeURIComponent(name)}`).then((r) => r.data)
}
