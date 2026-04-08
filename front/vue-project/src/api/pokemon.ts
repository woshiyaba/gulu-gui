import axios from 'axios'
import type { Attribute, PokemonListResponse, PokemonDetail } from '@/types'

const http = axios.create({
  baseURL: 'http://localhost:8000',
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
