import { request } from '@/utils/request'
import type {
  Attribute,
  PokemonBodyMatchResponse,
  PokemonDetail,
  PokemonListResponse,
} from '@/types/pokemon'

export interface PokemonQuery {
  name?: string
  attr?: string
  page?: number
  page_size?: number
}

export interface PokemonBodyMatchQuery {
  height_m: number
  weight_kg: number
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
