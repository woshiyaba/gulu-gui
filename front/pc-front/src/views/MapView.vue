<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { fetchCategories, fetchMapPoints } from '@/api/pokemon'
import { useTheme } from '@/composables/useTheme'
import type { Category, MapPoint } from '@/types'

const { isDark, toggleTheme } = useTheme()

// ── 状态 ─────────────────────────────────────────────────
const categories = ref<Category[]>([])
const loading = ref(true)
const error = ref('')
// 选中的 category_id 集合（空 = 显示全部）
const selectedCategoryIds = ref<Set<number>>(new Set())
const mapContainer = ref<HTMLDivElement | null>(null)
let mapInstance: maplibregl.Map | null = null

// 每种 type 依次分配颜色
const COLOR_PALETTE = [
  '#7c93ff', '#4ade80', '#facc15', '#fb923c',
  '#f472b6', '#34d399', '#a78bfa', '#60a5fa',
  '#f87171', '#2dd4bf', '#e879f9', '#fbbf24',
]

// ── 按 type 分组（保留原始顺序） ──────────────────────────
const groupedCategories = computed(() => {
  const seen = new Map<string, Category[]>()
  for (const cat of categories.value) {
    if (!seen.has(cat.type)) seen.set(cat.type, [])
    seen.get(cat.type)!.push(cat)
  }
  return [...seen.entries()].map(([type, items]) => ({ type, items }))
})

// ── type → 颜色 ───────────────────────────────────────────
const typeColorMap = computed(() => {
  const result: Record<string, string> = {}
  groupedCategories.value.forEach(({ type }, i) => {
    result[type] = COLOR_PALETTE[i % COLOR_PALETTE.length]
  })
  return result
})

// ── 点击 category chip 切换选中 ───────────────────────────
function toggleCategory(categoryId: number) {
  const next = new Set(selectedCategoryIds.value)
  if (next.has(categoryId)) {
    next.delete(categoryId)
  } else {
    next.add(categoryId)
  }
  selectedCategoryIds.value = next
  applyMapFilter()
}

function clearFilter() {
  selectedCategoryIds.value = new Set()
  applyMapFilter()
}

// ── 更新地图点位 filter ───────────────────────────────────
function applyMapFilter() {
  if (!mapInstance) return
  const ids = [...selectedCategoryIds.value]
  // 无选中 → 显示全部；有选中 → 只显示匹配的
  const filter = ids.length === 0
    ? null
    : ['in', ['get', 'category_id'], ['literal', ids]] as maplibregl.FilterSpecification
  mapInstance.setFilter('poi-symbols', filter)
}

// ── 将点位数据转为 GeoJSON ────────────────────────────────
function buildGeoJSON(points: MapPoint[]) {
  return {
    type: 'FeatureCollection' as const,
    features: points
      .filter((p) => Number.isFinite(p.longitude) && Number.isFinite(p.latitude))
      .map((p) => ({
        type: 'Feature' as const,
        geometry: { type: 'Point' as const, coordinates: [p.longitude, p.latitude] },
        properties: {
          id: p.id,
          title: p.title,
          category_id: p.category_id,
          category_image_url: p.category_image_url,
          // symbol 图层通过此 key 找到对应图片
          icon_key: `cat-${p.category_id}`,
        },
      })),
  }
}

// ── 预加载所有唯一 category 图标到 maplibre 图片注册表 ────
async function loadCategoryImages(points: MapPoint[]) {
  // 收集唯一的 category_id → image_url，避免重复加载
  const unique = new Map<number, string>()
  for (const p of points) {
    if (!unique.has(p.category_id)) {
      unique.set(p.category_id, p.category_image_url)
    }
  }

  await Promise.all(
    [...unique.entries()].map(([catId, url]) =>
      new Promise<void>((resolve) => {
        const img = new Image()
        img.crossOrigin = 'anonymous'
        img.onload = () => {
          const key = `cat-${catId}`
          if (mapInstance && !mapInstance.hasImage(key)) {
            mapInstance.addImage(key, img)
          }
          resolve()
        }
        // 加载失败时静默跳过，不阻塞其他图标
        img.onerror = () => resolve()
        img.src = url
      }),
    ),
  )
}

// ── 初始化 maplibre 地图 ──────────────────────────────────
function initMap(geoJson: ReturnType<typeof buildGeoJSON>, rawPoints: MapPoint[]) {
  if (!mapContainer.value) return

  mapInstance = new maplibregl.Map({
    container: mapContainer.value,
    style: {
      version: 8,
      sources: {
        'rocom-raster': {
          type: 'raster',
          tiles: ['http://101.126.137.23/images/tiles/rocom/4010_v3_7f2d9c/{z}/{y}_{x}.png?v1'],
          tileSize: 256,
          maxzoom: 13,
          bounds: [-1.4, 0, 0, 1.4],
        },
      },
      layers: [
        { id: 'rocom', type: 'raster', source: 'rocom-raster', minzoom: 9, maxzoom: 13 },
      ],
    },
    minZoom: 9,
    maxZoom: 13,
    bounds: [[-1.4, 0], [0, 1.4]],
    center: [-0.7, 0.7],
    zoom: 11,
  })

  mapInstance.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right')

  const popup = new maplibregl.Popup({
    closeButton: false,
    closeOnClick: true,
    maxWidth: '260px',
  })

  mapInstance.on('load', async () => {
    // 先加载所有图标图片，再添加图层，避免 symbol 找不到图片
    await loadCategoryImages(rawPoints)

    mapInstance!.addSource('poi-source', { type: 'geojson', data: geoJson })

    mapInstance!.addLayer({
      id: 'poi-symbols',
      type: 'symbol',
      source: 'poi-source',
      layout: {
        // 取 feature 的 icon_key 属性匹配已注册图片
        'icon-image': ['get', 'icon_key'],
        'icon-size': [
          'interpolate', ['linear'], ['zoom'],
          9, 0.25,
          11, 0.45,
          13, 0.65,
        ],
        'icon-allow-overlap': true,
        'icon-ignore-placement': true,
      },
    })

    mapInstance!.on('mouseenter', 'poi-symbols', () => {
      mapInstance!.getCanvas().style.cursor = 'pointer'
    })
    mapInstance!.on('mouseleave', 'poi-symbols', () => {
      mapInstance!.getCanvas().style.cursor = ''
    })

    mapInstance!.on('click', 'poi-symbols', (e) => {
      const feature = e.features?.[0]
      if (!feature) return

      const geom = feature.geometry as { type: 'Point'; coordinates: [number, number] }
      const { title, category_image_url } = feature.properties as {
        title: string
        category_image_url: string
      }

      popup
        .setLngLat(geom.coordinates)
        .setHTML(`
          <div style="display:flex;align-items:center;gap:8px;font-size:13px;line-height:1.4;padding:2px 0;">
            <img src="${category_image_url}" width="32" height="32" style="object-fit:contain;flex-shrink:0;" onerror="this.style.display='none'" />
            <span style="font-weight:600;word-break:break-all;">${title}</span>
          </div>
        `)
        .addTo(mapInstance!)
    })
  })
}

// ── 初始化：并行拉取数据，再初始化地图 ───────────────────
onMounted(async () => {
  try {
    const [cats, points] = await Promise.all([
      fetchCategories(),
      fetchMapPoints(),
    ])
    categories.value = cats
    const geoJson = buildGeoJSON(points)
    initMap(geoJson, points)
  } catch {
    error.value = '加载失败，请确认后端服务已启动（uvicorn api.main:app --port 8000）'
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  mapInstance?.remove()
  mapInstance = null
})
</script>

<template>
  <div class="map-page">
    <!-- 顶部导航栏 -->
    <header class="map-header">
      <RouterLink class="nav-link-btn" to="/">← 返回首页</RouterLink>
      <h1 class="map-title">洛克王国世界地图</h1>
      <button class="theme-btn" @click="toggleTheme">
        {{ isDark ? '切换浅色' : '夜间模式' }}
      </button>
    </header>

    <!-- 主体：左侧面板 + 右侧地图 -->
    <div class="map-body">
      <!-- 左侧 category 面板 -->
      <aside class="category-panel">
        <div class="panel-toolbar">
          <span class="panel-title">分类筛选</span>
          <button
            v-if="selectedCategoryIds.size > 0"
            class="clear-btn"
            @click="clearFilter"
          >
            清除 ({{ selectedCategoryIds.size }})
          </button>
        </div>

        <div v-if="loading" class="panel-loading">加载中...</div>
        <div v-else-if="error" class="panel-error">{{ error }}</div>

        <!-- 按 type 分组渲染 -->
        <div v-for="group in groupedCategories" :key="group.type" class="type-group">
          <div class="type-heading">
            <span
              class="type-dot"
              :style="{ background: typeColorMap[group.type] }"
            />
            {{ group.type }}
          </div>
          <div class="category-grid">
            <button
              v-for="cat in group.items"
              :key="cat.category_id"
              class="category-chip"
              :class="{ selected: selectedCategoryIds.has(cat.category_id) }"
              :style="selectedCategoryIds.has(cat.category_id)
                ? { borderColor: typeColorMap[group.type], background: typeColorMap[group.type] + '22' }
                : {}"
              @click="toggleCategory(cat.category_id)"
            >
              <img
                :src="cat.category_image_url"
                :alt="cat.description"
                class="chip-icon"
                onerror="this.style.display='none'"
              />
              <span class="chip-label">{{ cat.description }}</span>
            </button>
          </div>
        </div>
      </aside>

      <!-- 右侧地图容器 -->
      <div class="map-wrap">
        <div v-if="loading" class="map-overlay">
          <span class="loading-text">地图加载中...</span>
        </div>
        <div v-if="error" class="map-overlay error-overlay">
          <span>{{ error }}</span>
        </div>
        <div ref="mapContainer" class="map-container" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.map-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg);
  overflow: hidden;
}

/* ── 顶部导航 ─────────────────────────────────────────── */
.map-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  z-index: 10;
}

.map-title {
  flex: 1;
  font-size: 18px;
  font-weight: 700;
  color: var(--color-accent);
  margin: 0;
}

.nav-link-btn {
  padding: 7px 14px;
  border: 1px solid var(--color-border);
  border-radius: 20px;
  background: transparent;
  color: var(--color-text);
  font-size: 13px;
  text-decoration: none;
  white-space: nowrap;
  transition: all 0.2s;
}

.nav-link-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: var(--color-hover);
}

.theme-btn {
  padding: 7px 14px;
  border: 1px solid var(--color-border);
  border-radius: 20px;
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.theme-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: var(--color-hover);
}

/* ── 主体 ─────────────────────────────────────────────── */
.map-body {
  flex: 1;
  display: flex;
  min-height: 0;
}

/* ── 左侧面板 ─────────────────────────────────────────── */
.category-panel {
  width: 280px;
  flex-shrink: 0;
  overflow-y: auto;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.panel-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px 8px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 4px;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-muted);
  letter-spacing: 0.5px;
}

.clear-btn {
  padding: 3px 10px;
  border: 1px solid var(--color-accent);
  border-radius: 12px;
  background: transparent;
  color: var(--color-accent);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.clear-btn:hover {
  background: var(--color-hover);
}

.panel-loading,
.panel-error {
  padding: 20px 8px;
  font-size: 13px;
  color: var(--color-muted);
  text-align: center;
}

.panel-error {
  color: #f87171;
}

/* ── type 分组 ────────────────────────────────────────── */
.type-group {
  margin-bottom: 8px;
}

.type-heading {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  color: var(--color-muted);
  padding: 4px 4px 6px;
  letter-spacing: 0.3px;
}

.type-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* category chip 两列排布 */
.category-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 5px;
}

.category-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 7px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: transparent;
  color: var(--color-text);
  font-size: 12px;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s;
  min-width: 0;
}

.category-chip:hover {
  border-color: var(--color-accent);
  background: var(--color-hover);
}

.category-chip.selected {
  color: var(--color-text);
}

.chip-icon {
  width: 20px;
  height: 20px;
  object-fit: contain;
  flex-shrink: 0;
}

.chip-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
  line-height: 1.3;
}

/* ── 右侧地图 ─────────────────────────────────────────── */
.map-wrap {
  flex: 1;
  position: relative;
  min-width: 0;
}

.map-container {
  width: 100%;
  height: 100%;
}

.map-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  z-index: 5;
  font-size: 15px;
  color: var(--color-muted);
}

.error-overlay {
  color: #f87171;
  font-size: 14px;
}

.loading-text {
  animation: pulse 1.4s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

/* maplibre popup 样式覆盖 */
:deep(.maplibregl-popup-content) {
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 10px 12px;
  box-shadow: var(--color-shadow);
}

:deep(.maplibregl-popup-tip) {
  border-top-color: var(--color-surface) !important;
  border-bottom-color: var(--color-surface) !important;
}

@media (max-width: 768px) {
  .map-body {
    flex-direction: column;
  }

  .category-panel {
    width: 100%;
    height: 200px;
    border-right: none;
    border-bottom: 1px solid var(--color-border);
  }
}
</style>
