import { request } from '@/utils/request'
import type {
  Attribute,
  Category,
  MapPoint,
  PokemonBodyMatchResponse,
  PokemonDetail,
  PokemonEvolutionChain,
  PokemonListResponse,
  SkillListResponse,
  SkillStoneListResponse,
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
