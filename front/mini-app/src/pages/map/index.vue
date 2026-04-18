<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { fetchCategories, fetchMapPoints } from '@/api/pokemon'
import type { Category, MapPoint } from '@/types/pokemon'

const ZOOM = 11
const TILE_SIZE = 256
const N = Math.pow(2, ZOOM)
const TILE_URL_BASE = 'https://wikiroco.com/images/tiles/rocom/4010_v3_7f2d9c'

const MAP_BOUNDS = { west: -1.4, east: 0, south: 0, north: 1.4 }

function lngToTileX(lng: number) {
  return Math.floor(((lng + 180) / 360) * N)
}

function latToTileY(lat: number) {
  const latRad = (lat * Math.PI) / 180
  return Math.floor(((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * N)
}

function lngToPixel(lng: number) {
  return ((lng + 180) / 360) * N * TILE_SIZE
}

function latToPixel(lat: number) {
  const latRad = (lat * Math.PI) / 180
  return ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * N * TILE_SIZE
}

const tileXMin = lngToTileX(MAP_BOUNDS.west)
const tileXMax = lngToTileX(MAP_BOUNDS.east)
const tileYMin = latToTileY(MAP_BOUNDS.north)
const tileYMax = latToTileY(MAP_BOUNDS.south)

const gridCols = tileXMax - tileXMin + 1
const gridRows = tileYMax - tileYMin + 1
const mapWidthPx = gridCols * TILE_SIZE
const mapHeightPx = gridRows * TILE_SIZE

const originPixelX = tileXMin * TILE_SIZE
const originPixelY = tileYMin * TILE_SIZE

interface TileInfo {
  key: string
  url: string
  x: number
  y: number
}

const tiles: TileInfo[] = []
for (let ty = tileYMin; ty <= tileYMax; ty++) {
  for (let tx = tileXMin; tx <= tileXMax; tx++) {
    tiles.push({
      key: `${ty}_${tx}`,
      url: `${TILE_URL_BASE}/${ZOOM}/${ty}_${tx}.png?v1`,
      x: (tx - tileXMin) * TILE_SIZE,
      y: (ty - tileYMin) * TILE_SIZE,
    })
  }
}

const COLOR_PALETTE = [
  '#7c93ff', '#4ade80', '#facc15', '#fb923c',
  '#f472b6', '#34d399', '#a78bfa', '#60a5fa',
  '#f87171', '#2dd4bf', '#e879f9', '#fbbf24',
]

const EXTENDED_PALETTE = [
  '#e6194b', '#3cb44b', '#ffe119', '#4363d8',
  '#f58231', '#42d4f4', '#f032e6', '#bfef45',
  '#fabebe', '#469990', '#e6beff', '#9A6324',
  '#fffac8', '#800000', '#aaffc3', '#808000',
  '#ffd8b1', '#000075', '#a9a9a9', '#911eb4',
  '#46f0f0', '#bcf60c', '#008080', '#e6194b',
  '#ff6781', '#17becf', '#8c564b', '#2ca02c',
  '#d62728', '#9467bd', '#7f7f7f', '#1f77b4',
]

const HIGH_CONTRAST_PALETTE = [
  '#e6194b', '#3cb44b', '#4363d8', '#f58231',
  '#911eb4', '#42d4f4', '#f032e6', '#bfef45',
  '#fabebe', '#469990', '#e6beff', '#9A6324',
  '#800000', '#aaffc3', '#808000', '#000075',
  '#ffe119', '#ff6781', '#17becf', '#2ca02c',
]

const sysInfo = uni.getSystemInfoSync()
const screenWidth = sysInfo.windowWidth
const screenHeight = sysInfo.windowHeight
const navBarHeight = 88
const filterBarHeight = 50
const areaHeight = screenHeight - navBarHeight - filterBarHeight
const initialX = ref(Math.round(screenWidth / 2 - mapWidthPx / 2))
const initialY = ref(Math.round(areaHeight / 2 - mapHeightPx / 2))

const categories = ref<Category[]>([])
const allPoints = ref<MapPoint[]>([])
const loading = ref(true)
const error = ref('')
const DEFAULT_CATEGORY_IDS = [17310030035, 17310030047]
const selectedCategoryIds = ref<Set<number>>(new Set(DEFAULT_CATEGORY_IDS))
const filterOpen = ref(false)
const activePopup = ref<{ title: string; color: string; x: number; y: number } | null>(null)

const groupedCategories = computed(() => {
  const seen = new Map<string, Category[]>()
  for (const cat of categories.value) {
    if (!seen.has(cat.type)) seen.set(cat.type, [])
    seen.get(cat.type)!.push(cat)
  }
  return [...seen.entries()].map(([type, items]) => ({ type, items }))
})

const typeColorMap = computed(() => {
  const result: Record<string, string> = {}
  groupedCategories.value.forEach(({ type }, i) => {
    result[type] = COLOR_PALETTE[i % COLOR_PALETTE.length]!
  })
  return result
})

const categoryIdToDefaultColor = computed(() => {
  const result: Record<number, string> = {}
  const allCats = categories.value
  allCats.forEach((cat, i) => {
    result[cat.category_id] = EXTENDED_PALETTE[i % EXTENDED_PALETTE.length]!
  })
  return result
})

const categoryIdToColor = computed(() => {
  const selected = selectedCategoryIds.value
  if (selected.size === 0) return categoryIdToDefaultColor.value

  const result: Record<number, string> = { ...categoryIdToDefaultColor.value }
  const selectedIds = [...selected]
  selectedIds.forEach((id, i) => {
    result[id] = HIGH_CONTRAST_PALETTE[i % HIGH_CONTRAST_PALETTE.length]!
  })
  return result
})

interface MarkerInfo {
  id: number
  title: string
  categoryId: number
  color: string
  px: number
  py: number
}

const markers = computed<MarkerInfo[]>(() => {
  const colorMap = categoryIdToColor.value
  return allPoints.value
    .filter((p) => Number.isFinite(p.longitude) && Number.isFinite(p.latitude))
    .map((p) => ({
      id: p.id,
      title: p.title,
      categoryId: p.category_id,
      color: colorMap[p.category_id] ?? '#8aa2c9',
      px: lngToPixel(p.longitude) - originPixelX,
      py: latToPixel(p.latitude) - originPixelY,
    }))
})

const visibleMarkers = computed(() => {
  if (selectedCategoryIds.value.size === 0) return markers.value
  return markers.value.filter((m) => selectedCategoryIds.value.has(m.categoryId))
})

function toggleCategory(categoryId: number) {
  const next = new Set(selectedCategoryIds.value)
  if (next.has(categoryId)) {
    next.delete(categoryId)
  } else {
    next.add(categoryId)
  }
  selectedCategoryIds.value = next
}

function clearFilter() {
  selectedCategoryIds.value = new Set()
}

function toggleFilterPanel() {
  filterOpen.value = !filterOpen.value
}

function onMarkerTap(marker: MarkerInfo) {
  if (activePopup.value && activePopup.value.title === marker.title) {
    activePopup.value = null
    return
  }
  activePopup.value = {
    title: marker.title,
    color: marker.color,
    x: marker.px,
    y: marker.py,
  }
}

function closePopup() {
  activePopup.value = null
}

onLoad(async () => {
  try {
    const [cats, points] = await Promise.all([
      fetchCategories(),
      fetchMapPoints(),
    ])
    categories.value = cats
    allPoints.value = points
  } catch {
    error.value = '地图数据加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <view class="page">
    <view v-if="loading" class="loading-box">
      <text class="loading-text">地图加载中...</text>
    </view>

    <view v-else-if="error" class="error-box">
      <text class="error-text">{{ error }}</text>
    </view>

    <view v-else class="map-container">
      <movable-area class="movable-area">
        <movable-view
          class="movable-view"
          direction="all"
          :scale="true"
          :scale-min="0.3"
          :scale-max="3"
          :x="initialX"
          :y="initialY"
          :style="{ width: mapWidthPx + 'px', height: mapHeightPx + 'px' }"
          @tap="closePopup"
        >
          <view
            class="tile-grid"
            :style="{ width: mapWidthPx + 'px', height: mapHeightPx + 'px' }"
          >
            <image
              v-for="tile in tiles"
              :key="tile.key"
              class="tile-image"
              :src="tile.url"
              :style="{
                left: tile.x + 'px',
                top: tile.y + 'px',
                width: TILE_SIZE + 'px',
                height: TILE_SIZE + 'px',
              }"
              mode="scaleToFill"
            />
          </view>

          <view
            v-for="marker in visibleMarkers"
            :key="marker.id"
            class="marker-dot"
            :style="{
              left: (marker.px - 6) + 'px',
              top: (marker.py - 6) + 'px',
              background: marker.color,
              boxShadow: '0 0 0 2px #fff, 0 1px 4px rgba(0,0,0,0.3)',
            }"
            @tap.stop="onMarkerTap(marker)"
          />

          <view
            v-if="activePopup"
            class="popup"
            :style="{ left: activePopup.x + 'px', top: (activePopup.y - 40) + 'px' }"
            @tap.stop
          >
            <view class="popup-dot" :style="{ background: activePopup.color }" />
            <text class="popup-title">{{ activePopup.title }}</text>
          </view>
        </movable-view>
      </movable-area>

      <view class="filter-bar" @tap="toggleFilterPanel">
        <text class="filter-bar-text">
          分类筛选
          <text v-if="selectedCategoryIds.size > 0" class="filter-count">
            ({{ selectedCategoryIds.size }}个已选)
          </text>
        </text>
        <text class="filter-arrow">{{ filterOpen ? '▼' : '▲' }}</text>
      </view>

      <view v-if="filterOpen" class="filter-panel">
        <scroll-view class="filter-scroll" scroll-y>
          <view v-if="selectedCategoryIds.size > 0" class="clear-row">
            <button class="clear-btn" @tap="clearFilter">清除筛选</button>
          </view>

          <view
            v-for="group in groupedCategories"
            :key="group.type"
            class="filter-group"
          >
            <text class="group-title" :style="{ color: typeColorMap[group.type] }">
              {{ group.type }}
            </text>
            <view class="group-chips">
              <view
                v-for="cat in group.items"
                :key="cat.category_id"
                class="category-chip"
                :class="{ selected: selectedCategoryIds.has(cat.category_id) }"
                :style="selectedCategoryIds.has(cat.category_id) ? {
                  borderColor: categoryIdToColor[cat.category_id],
                  background: categoryIdToColor[cat.category_id] + '18',
                } : {}"
                @tap="toggleCategory(cat.category_id)"
              >
                <image
                  v-if="cat.category_image_url"
                  class="chip-image"
                  :src="cat.category_image_url"
                  mode="aspectFit"
                />
                <view
                  v-else
                  class="chip-color-dot"
                  :style="{ background: categoryIdToColor[cat.category_id] }"
                />
                <text class="chip-text">{{ cat.description }}</text>
              </view>
            </view>
          </view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #eef3fb;
  overflow: hidden;
}

.loading-box,
.error-box {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-text {
  font-size: 28rpx;
  color: #6d87b1;
}

.error-text {
  font-size: 28rpx;
  color: #c74646;
  padding: 40rpx;
  text-align: center;
}

.map-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.movable-area {
  flex: 1;
  width: 100%;
  overflow: hidden;
}

.movable-view {
  position: relative;
}

.tile-grid {
  position: relative;
}

.tile-image {
  position: absolute;
  display: block;
}

.marker-dot {
  position: absolute;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  z-index: 10;
}

.popup {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: #ffffff;
  border-radius: 14px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.18);
  z-index: 20;
  transform: translateX(-50%);
  white-space: nowrap;
}

.popup-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.popup-title {
  font-size: 26rpx;
  font-weight: 600;
  color: #1f3760;
}

.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20rpx 28rpx;
  background: #ffffff;
  border-top: 1rpx solid #e7eefb;
}

.filter-bar-text {
  font-size: 28rpx;
  font-weight: 600;
  color: #214887;
}

.filter-count {
  font-size: 24rpx;
  font-weight: 400;
  color: #2b74ff;
  margin-left: 8rpx;
}

.filter-arrow {
  font-size: 24rpx;
  color: #8aa2c9;
}

.filter-panel {
  background: #ffffff;
  border-top: 1rpx solid #e7eefb;
  max-height: 50vh;
}

.filter-scroll {
  max-height: 50vh;
  padding: 20rpx 28rpx 40rpx;
}

.clear-row {
  margin-bottom: 20rpx;
}

.clear-btn {
  margin: 0;
  padding: 0 24rpx;
  height: 60rpx;
  line-height: 60rpx;
  border: 1rpx solid #d85b5b;
  border-radius: 999rpx;
  background: rgba(216, 91, 91, 0.08);
  color: #d85b5b;
  font-size: 24rpx;
}

.clear-btn::after {
  border: none;
}

.filter-group {
  margin-bottom: 24rpx;
}

.group-title {
  display: block;
  font-size: 26rpx;
  font-weight: 700;
  margin-bottom: 14rpx;
}

.group-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}

.category-chip {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  padding: 12rpx 18rpx;
  border: 2rpx solid #dbe4f3;
  border-radius: 999rpx;
  background: #f8faff;
  transition: all 0.15s;
}

.category-chip.selected {
  border-width: 2rpx;
}

.chip-image {
  width: 36rpx;
  height: 36rpx;
  flex-shrink: 0;
}

.chip-color-dot {
  width: 18rpx;
  height: 18rpx;
  border-radius: 50%;
  flex-shrink: 0;
}

.chip-text {
  font-size: 22rpx;
  color: #45638e;
  white-space: nowrap;
}
</style>
