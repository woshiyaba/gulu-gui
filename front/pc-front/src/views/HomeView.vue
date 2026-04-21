<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AttributeFilter from '@/components/AttributeFilter.vue'
import EggGroupFilter from '@/components/EggGroupFilter.vue'
import PokemonCard from '@/components/PokemonCard.vue'
import { fetchAttributes, fetchEggGroups, fetchPokemon } from '@/api/pokemon'
import { useTheme } from '@/composables/useTheme'
import type { Attribute, Pokemon } from '@/types'

// ── 状态 ─────────────────────────────────────────────────
const attributes = ref<Attribute[]>([])
const eggGroups = ref<string[]>([])
const pokemons = ref<Pokemon[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')

const searchName = ref('')
const selectedAttrs = ref<string[]>([])
const selectedEggGroups = ref<string[]>([])
const selectedSortBy = ref<'no' | 'total_stats' | 'hp' | 'atk' | 'matk' | 'def_val' | 'mdef' | 'spd'>('no')
const selectedSortDir = ref<'asc' | 'desc'>('asc')
const currentPage = ref(1)
const pageSize = 30
const { isDark, toggleTheme } = useTheme()
const loadMoreRef = ref<HTMLElement | null>(null)
let searchTimer: ReturnType<typeof setTimeout> | undefined
let loadMoreObserver: IntersectionObserver | null = null

const isInitialLoading = computed(() => loading.value && pokemons.value.length === 0)
const hasMore = computed(() => pokemons.value.length < total.value)
const SORT_OPTIONS = [
  { value: 'no', label: '图鉴编号' },
  { value: 'total_stats', label: '总种族值' },
  { value: 'spd', label: '速度' },
  { value: 'atk', label: '物攻' },
  { value: 'matk', label: '魔攻' },
  { value: 'def_val', label: '物防' },
  { value: 'mdef', label: '魔防' },
  { value: 'hp', label: 'HP' },
] as const

function disconnectLoadMoreObserver() {
  loadMoreObserver?.disconnect()
  loadMoreObserver = null
}

function setupLoadMoreObserver() {
  disconnectLoadMoreObserver()
  if (!loadMoreRef.value) return

  // 提前一点触发下一页，滚动到底前就开始预加载。
  loadMoreObserver = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting) {
        void loadNextPage()
      }
    },
    { rootMargin: '240px 0px' },
  )

  loadMoreObserver.observe(loadMoreRef.value)
}

// ── 请求精灵列表 ──────────────────────────────────────────
async function loadPokemon(reset = false) {
  if (loading.value) return

  if (reset) {
    currentPage.value = 1
    pokemons.value = []
    total.value = 0
  }

  loading.value = true
  error.value = ''
  try {
    const res = await fetchPokemon({
      name: searchName.value || undefined,
      attr: selectedAttrs.value.length ? selectedAttrs.value : undefined,
      egg_group: selectedEggGroups.value.length ? selectedEggGroups.value : undefined,
      order_by: selectedSortBy.value,
      order_dir: selectedSortDir.value,
      page: currentPage.value,
      page_size: pageSize,
    })

    pokemons.value = reset
      ? res.items
      : [...pokemons.value, ...res.items]
    total.value = res.total
  } catch {
    error.value = '加载失败，请确认后端服务已启动（uvicorn api.main:app --port 8000）'
  } finally {
    loading.value = false
  }
}

async function resetAndLoadPokemon() {
  await loadPokemon(true)
  await nextTick()
  setupLoadMoreObserver()
}

async function loadNextPage() {
  if (loading.value || !hasMore.value || !!error.value) return

  currentPage.value += 1
  await loadPokemon()
  if (error.value) {
    currentPage.value -= 1
  }
}

// ── 筛选条件变化时重置到第一页 ────────────────────────────
function onAttrChange(attrs: string[]) {
  selectedAttrs.value = attrs
}

function onEggGroupChange(groups: string[]) {
  selectedEggGroups.value = groups
}

function onSearch() {
  void resetAndLoadPokemon()
}

// 搜索框防抖：300ms 后触发请求
watch(searchName, () => {
  if (searchTimer) {
    clearTimeout(searchTimer)
  }
  searchTimer = setTimeout(() => {
    void resetAndLoadPokemon()
  }, 300)
})

watch(selectedAttrs, () => {
  void resetAndLoadPokemon()
})

watch(selectedEggGroups, () => {
  void resetAndLoadPokemon()
})

watch([selectedSortBy, selectedSortDir], () => {
  void resetAndLoadPokemon()
})

watch(loadMoreRef, () => {
  setupLoadMoreObserver()
})

// ── 初始化 ────────────────────────────────────────────────
onMounted(async () => {
  const [attrs, eggs] = await Promise.all([
    fetchAttributes().catch(() => []),
    fetchEggGroups().catch(() => []),
  ])
  attributes.value = attrs
  eggGroups.value = eggs
  await resetAndLoadPokemon()
})

onBeforeUnmount(() => {
  if (searchTimer) {
    clearTimeout(searchTimer)
  }
  disconnectLoadMoreObserver()
})
</script>

<template>
  <div class="app">
    <!-- 顶部标题 -->
    <header class="app-header">
      <h1 class="app-title">洛克王国精灵图鉴</h1>

      <!-- 搜索框 -->
      <div class="search-wrap">
        <input
          v-model="searchName"
          class="search-input"
          placeholder="搜索精灵名称..."
          @keyup.enter="onSearch"
        />
        <span class="search-icon">🔍</span>
      </div>

      <RouterLink class="nav-link-btn" to="/map">世界地图</RouterLink>
      <RouterLink class="nav-link-btn" to="/body-match">量体查宠</RouterLink>
      <RouterLink class="nav-link-btn" to="/skill-stones">技能石查询</RouterLink>
      <RouterLink class="nav-link-btn" to="/skills">技能图鉴</RouterLink>
      <RouterLink class="nav-link-btn" to="/lineups">阵容推荐</RouterLink>

      <button class="theme-btn" @click="toggleTheme">
        {{ isDark ? '切换浅色' : '夜间模式' }}
      </button>
    </header>

    <main class="app-main">
      <!-- 属性筛选栏 -->
      <EggGroupFilter
        :groups="eggGroups"
        :selected="selectedEggGroups"
        @change="onEggGroupChange"
      />
      <AttributeFilter
        :attributes="attributes"
        :selected="selectedAttrs"
        @change="onAttrChange"
      />

      <!-- 结果统计 -->
      <div class="result-info">
        <span v-if="total > 0">已展示 {{ pokemons.length }} / {{ total }} 只精灵</span>
        <span v-else-if="loading">加载中...</span>
        <span v-else>共 0 只精灵</span>
        <div class="sort-controls">
          <label class="sort-label" for="sort-by">排序</label>
          <select id="sort-by" v-model="selectedSortBy" class="sort-select">
            <option v-for="opt in SORT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
          <select v-model="selectedSortDir" class="sort-select">
            <option value="asc">升序</option>
            <option value="desc">降序</option>
          </select>
        </div>
      </div>

      <!-- 错误提示 -->
      <div v-if="error" class="error-msg">{{ error }}</div>

      <!-- 精灵卡片 Grid -->
      <div v-if="isInitialLoading" class="skeleton-grid">
        <div v-for="n in 12" :key="n" class="skeleton-card"></div>
      </div>
      <div v-else-if="pokemons.length === 0 && !error" class="empty-msg">
        没有找到匹配的精灵
      </div>
      <div v-else class="pokemon-grid">
        <PokemonCard v-for="p in pokemons" :key="p.no" :pokemon="p" />
      </div>

      <!-- 瀑布流加载提示 -->
      <div v-if="pokemons.length > 0 && !error" ref="loadMoreRef" class="load-more-anchor">
        <span v-if="loading" class="load-more-text">正在加载更多...</span>
        <span v-else-if="hasMore" class="load-more-text">继续下滑加载更多</span>
        <span v-else class="load-more-text">已经到底啦</span>
      </div>
    </main>
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
  background: var(--color-bg);
}

.app-header {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  padding: 16px 24px;
  display: flex;
  align-items: center;
  gap: 24px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.app-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-accent);
  white-space: nowrap;
  margin: 0;
}

.search-wrap {
  flex: 1;
  position: relative;
  max-width: 400px;
}

.theme-btn {
  padding: 8px 16px;
  border: 1px solid var(--color-border);
  border-radius: 20px;
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.nav-link-btn {
  padding: 8px 16px;
  border: 1px solid var(--color-accent);
  border-radius: 20px;
  background: transparent;
  color: var(--color-accent);
  font-size: 13px;
  text-decoration: none;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.nav-link-btn:hover {
  background: var(--color-hover);
}

.theme-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: var(--color-hover);
}

.search-input {
  width: 100%;
  padding: 8px 36px 8px 14px;
  border: 2px solid var(--color-border);
  border-radius: 24px;
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.search-input:focus {
  border-color: var(--color-accent);
}

.search-icon {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 14px;
  pointer-events: none;
}

.app-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 16px 24px 40px;
}

.result-info {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 12px;
  font-size: 13px;
  color: var(--color-muted);
  margin-bottom: 16px;
}

.sort-controls {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.sort-label {
  color: var(--color-muted);
}

.sort-select {
  height: 30px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 12px;
  padding: 0 8px;
}

.error-msg {
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #f87171;
  font-size: 14px;
  margin-bottom: 16px;
}

.empty-msg {
  text-align: center;
  padding: 80px 0;
  color: var(--color-muted);
  font-size: 16px;
}

/* 卡片网格 */
.pokemon-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

/* 骨架屏 */
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.skeleton-card {
  height: 240px;
  border-radius: 12px;
  background: var(--color-surface);
  animation: shimmer 1.4s infinite;
}

@keyframes shimmer {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}

/* 瀑布流加载提示 */
.load-more-anchor {
  display: flex;
  justify-content: center;
  padding: 28px 0 12px;
}

.load-more-text {
  font-size: 13px;
  color: var(--color-muted);
}

@media (max-width: 720px) {
  .app-header {
    flex-wrap: wrap;
    gap: 12px;
  }

  .search-wrap {
    order: 3;
    max-width: none;
    width: 100%;
  }
}
</style>
