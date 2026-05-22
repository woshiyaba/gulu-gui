import axios from 'axios'

const DEFAULT_API_BASE_URL = import.meta.env.PROD
  ? 'https://wikiroco.com'
  : 'http://localhost:8000'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/+$/, '')

const http = axios.create({
  baseURL: apiBaseUrl,
  timeout: 10000,
})

export interface AnnouncementLikeResponse {
  like_count: number
}

export const ANNOUNCEMENT_LIKED_STORAGE_KEY = 'wikiroco_announcement_liked'

export function hasLikedAnnouncementLocally(): boolean {
  try {
    return localStorage.getItem(ANNOUNCEMENT_LIKED_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function markAnnouncementLikedLocally(): void {
  try {
    localStorage.setItem(ANNOUNCEMENT_LIKED_STORAGE_KEY, '1')
  } catch {
    /* ignore quota / private mode */
  }
}

export async function fetchAnnouncementLikeCount(): Promise<number> {
  const { data } = await http.get<AnnouncementLikeResponse>('/api/announcement/likes')
  return data.like_count
}

export async function likeAnnouncement(): Promise<number> {
  const { data } = await http.post<AnnouncementLikeResponse>('/api/announcement/likes')
  return data.like_count
}
