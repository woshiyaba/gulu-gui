import { request } from '@/utils/request'

export type ChangeEggStatus = 'open' | 'matched' | 'closed'

export interface ChangeEggListing {
  id: number
  user_id: number
  game_id: string
  own_pokemon_id: number
  own_tag: string
  want_pokemon_id: number
  want_tag: string
  status: ChangeEggStatus | string
  own_pokemon_name: string | null
  own_pokemon_avatar: string | null
  want_pokemon_name: string | null
  want_pokemon_avatar: string | null
  created_at: string | null
  updated_at: string | null
}

export interface ChangeEggCreatePayload {
  user_id: number | string
  game_id: string
  own_pokemon_id: number
  own_tag: string
  want_pokemon_id: number
  want_tag: string
}

export interface ChangeEggTag {
  code: string
  label: string
  sort_order: number
}

/** 查询我发布的换蛋挂单，可选按状态筛选。 */
export function fetchMyListings(userId: number | string, status?: ChangeEggStatus | '') {
  return request<ChangeEggListing[]>({
    url: '/api/change-eggs',
    data: { user_id: userId, status: status || undefined },
  })
}

/** 广场分页浏览所有匹配中的挂单。 */
export function fetchSquareListings(params: {
  limit?: number
  offset?: number
  pokemon_id?: number
  tag?: string
} = {}) {
  return request<ChangeEggListing[]>({
    url: '/api/change-eggs/square',
    data: params,
  })
}

/** 可选的蛋组 tag（大块头 / 小不点等）。 */
export function fetchEggTags() {
  return request<ChangeEggTag[]>({ url: '/api/change-eggs/tags' })
}

/** 发布一条换蛋挂单。 */
export function createListing(payload: ChangeEggCreatePayload) {
  return request<ChangeEggListing>({
    url: '/api/change-eggs',
    method: 'POST',
    data: payload,
  })
}

/** 主动关闭正在匹配（open）的挂单。 */
export function closeListing(listingId: number, userId: number | string) {
  return request<ChangeEggListing>({
    url: `/api/change-eggs/${listingId}/close`,
    method: 'POST',
    data: { user_id: userId },
  })
}

/** 彻底删除自己的挂单（user_id 走 query，便于后端 Query 校验归属）。 */
export function deleteListing(listingId: number, userId: number | string) {
  return request<{ ok: boolean }>({
    url: `/api/change-eggs/${listingId}?user_id=${encodeURIComponent(String(userId))}`,
    method: 'DELETE',
  })
}
