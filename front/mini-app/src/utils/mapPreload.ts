import { fetchCategories, fetchMapPoints } from '@/api/pokemon'
import type { Category, MapPoint } from '@/types/pokemon'

export interface MapPreloadResult {
  categories: Category[]
  points: MapPoint[]
}

let cached: Promise<MapPreloadResult> | null = null

export function preloadMapData(): Promise<MapPreloadResult> {
  if (cached) return cached
  cached = Promise.all([fetchCategories(), fetchMapPoints()])
    .then(([categories, points]) => ({ categories, points }))
    .catch((err) => {
      cached = null
      throw err
    })
  return cached
}
