<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import AttributeFilter from '@/components/AttributeFilter.vue'
import PokemonCard from '@/components/PokemonCard.vue'
import { fetchAttributes, fetchPokemon } from '@/api/pokemon'
import { useTheme } from '@/composables/useTheme'
import type { Attribute, Pokemon } from '@/types'

// ── 状态 ─────────────────────────────────────────────────
const attributes = ref<Attribute[]>([])
const pokemons = ref<Pokemon[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')

const searchName = ref('')
const selectedAttr = ref('')
const currentPage = ref(1)
const pageSize = 30
const { isDark, toggleTheme } = useTheme()

// ── 计算总页数 ────────────────────────────────────────────
const totalPages = () => Math.max(1, Math.ceil(total.value / pageSize))

// ── 请求精灵列表 ──────────────────────────────────────────
async function loadPokemon() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchPokemon({
      name: searchName.value || undefined,
      attr: selectedAttr.value || undefined,
      page: currentPage.value,
      page_size: pageSize,
    })
    pokemons.value = res.items
    total.value = res.total
  } catch {
    error.value = '加载失败，请确认后端服务已启动（uvicorn api.main:app --port 8000）'
  } finally {
    loading.value = false
  }
}

// ── 筛选条件变化时重置到第一页 ────────────────────────────
function onAttrChange(attr: string) {
  selectedAttr.value = attr
  currentPage.value = 1
}

function onSearch() {
  currentPage.value = 1
}

// 搜索框防抖：300ms 后触发请求
let searchTimer: ReturnType<typeof setTimeout>
watch(searchName, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    loadPokemon()
  }, 300)
})

watch([selectedAttr, currentPage], loadPokemon)

// ── 初始化 ────────────────────────────────────────────────
onMounted(async () => {
  attributes.value = await fetchAttributes().catch(() => [])
  loadPokemon()
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

      <button class="theme-btn" @click="toggleTheme">
        {{ isDark ? '切换浅色' : '夜间模式' }}
      </button>
    </header>

    <main class="app-main">
      <!-- 属性筛选栏 -->
      <AttributeFilter
        :attributes="attributes"
        :selected="selectedAttr"
        @change="onAttrChange"
      />

      <!-- 结果统计 -->
      <div class="result-info">
        <span v-if="!loading">共 {{ total }} 只精灵</span>
        <span v-else>加载中...</span>
      </div>

      <!-- 错误提示 -->
      <div v-if="error" class="error-msg">{{ error }}</div>

      <!-- 精灵卡片 Grid -->
      <div v-if="loading" class="skeleton-grid">
        <div v-for="n in 12" :key="n" class="skeleton-card"></div>
      </div>
      <div v-else-if="pokemons.length === 0 && !error" class="empty-msg">
        没有找到匹配的精灵
      </div>
      <div v-else class="pokemon-grid">
        <PokemonCard v-for="p in pokemons" :key="p.no" :pokemon="p" />
      </div>

      <!-- 分页 -->
      <div v-if="totalPages() > 1" class="pagination">
        <button
          class="page-btn"
          :disabled="currentPage === 1"
          @click="currentPage--"
        >上一页</button>

        <span class="page-info">{{ currentPage }} / {{ totalPages() }}</span>

        <button
          class="page-btn"
          :disabled="currentPage >= totalPages()"
          @click="currentPage++"
        >下一页</button>
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
  font-size: 13px;
  color: var(--color-muted);
  margin-bottom: 16px;
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

/* 分页 */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 32px;
}

.page-btn {
  padding: 8px 20px;
  border: 2px solid var(--color-accent);
  border-radius: 20px;
  background: transparent;
  color: var(--color-accent);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.page-btn:hover:not(:disabled) {
  background: var(--color-accent);
  color: #fff;
}

.page-btn:disabled {
  border-color: var(--color-border);
  color: var(--color-muted);
  cursor: not-allowed;
}

.page-info {
  font-size: 14px;
  color: var(--color-text);
  min-width: 80px;
  text-align: center;
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
