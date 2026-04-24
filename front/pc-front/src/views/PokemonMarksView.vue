<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchPokemonMarks } from '@/api/pokemon'
import { useTheme } from '@/composables/useTheme'
import type { PokemonMark } from '@/types'

const router = useRouter()
const { isDark, toggleTheme } = useTheme()

const keyword = ref('')
const loading = ref(false)
const error = ref('')
const marks = ref<PokemonMark[]>([])
const hasLoaded = ref(false)

const filteredMarks = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  const sorted = [...marks.value].sort((a, b) => a.sort_order - b.sort_order)
  if (!kw) return sorted
  return sorted.filter((item) => item.zh_name.toLowerCase().includes(kw))
})

const summaryText = computed(() => {
  if (!hasLoaded.value) return ''
  if (keyword.value.trim()) {
    return `关键词“${keyword.value.trim()}”共匹配到 ${filteredMarks.value.length} 条词条。`
  }
  return `当前共收录 ${marks.value.length} 条词条。`
})

async function loadMarks() {
  loading.value = true
  error.value = ''
  try {
    const list = await fetchPokemonMarks()
    marks.value = list ?? []
    hasLoaded.value = true
  } catch {
    error.value = '查询失败，请确认后端服务已启动且名词数据已导入'
    marks.value = []
    hasLoaded.value = true
  } finally {
    loading.value = false
  }
}

function onReset() {
  keyword.value = ''
}

onMounted(() => {
  void loadMarks()
})
</script>

<template>
  <div class="mark-page">
    <header class="page-header">
      <button class="back-btn" @click="router.push('/')">← 返回图鉴</button>
      <h1 class="page-title">名词解释</h1>
      <button class="theme-btn" @click="toggleTheme">
        {{ isDark ? '切换浅色' : '夜间模式' }}
      </button>
    </header>

    <main class="page-main">
      <section class="card search-card">
        <h2 class="section-title">按名字搜索</h2>
        <p class="helper-text">印记、状态、增益、减益、环境等战斗术语的详细说明，支持按名字模糊搜索。</p>

        <div class="search-row">
          <input
            v-model="keyword"
            class="search-input"
            type="text"
            placeholder="例如：印记、中毒、雨天"
          />
          <button class="action-btn secondary-btn" :disabled="loading" @click="onReset">
            重置
          </button>
        </div>
      </section>

      <div v-if="error" class="error-msg">{{ error }}</div>

      <section v-if="hasLoaded" class="card result-card">
        <div class="result-head">
          <h2 class="section-title">词条列表</h2>
          <span class="result-summary">{{ summaryText }}</span>
        </div>

        <div v-if="loading" class="skeleton-grid">
          <div v-for="n in 6" :key="n" class="skeleton-card"></div>
        </div>

        <div v-else-if="filteredMarks.length === 0" class="empty-msg">
          没有找到匹配的词条
        </div>

        <div v-else class="mark-grid">
          <article v-for="item in filteredMarks" :key="item.id" class="mark-card">
            <div class="mark-icon-wrap">
              <img
                v-if="item.image"
                :src="item.image"
                :alt="item.zh_name"
                class="mark-icon"
                loading="lazy"
              />
              <div v-else class="mark-icon-placeholder">
                {{ item.zh_name.slice(0, 1) }}
              </div>
            </div>
            <div class="mark-body">
              <h3 class="mark-name">{{ item.zh_name }}</h3>
              <p class="mark-desc">{{ item.zh_description }}</p>
            </div>
          </article>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.mark-page {
  min-height: 100vh;
  background: var(--color-bg);
}

.page-header {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  padding: 14px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.page-title {
  flex: 1;
  margin: 0;
  font-size: 22px;
  color: var(--color-accent);
}

.back-btn,
.theme-btn,
.action-btn {
  border-radius: 20px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.back-btn {
  padding: 6px 16px;
  border: 2px solid var(--color-accent);
  background: transparent;
  color: var(--color-accent);
}

.theme-btn {
  padding: 8px 16px;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
}

.page-main {
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px;
}

.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
}

.section-title {
  margin: 0 0 12px;
  font-size: 20px;
  color: var(--color-text);
}

.helper-text,
.result-summary {
  color: var(--color-muted);
  font-size: 14px;
  line-height: 1.7;
}

.search-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 18px;
}

.search-input {
  flex: 1;
  min-width: 0;
  padding: 12px 14px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 14px;
  outline: none;
}

.search-input:focus {
  border-color: var(--color-accent);
}

.action-btn {
  padding: 10px 18px;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.secondary-btn {
  color: var(--color-muted);
}

.back-btn:hover,
.theme-btn:hover,
.action-btn:hover:not(:disabled) {
  background: var(--color-hover);
}

.error-msg {
  margin-bottom: 20px;
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  color: #f87171;
}

.result-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}

.mark-grid,
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.mark-card {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: var(--color-bg);
  box-shadow: var(--color-shadow);
}

.mark-icon-wrap {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  background: var(--color-img-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}

.mark-icon {
  width: 52px;
  height: 52px;
  object-fit: contain;
}

.mark-icon-placeholder {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-accent);
}

.mark-body {
  min-width: 0;
  flex: 1;
}

.mark-name {
  margin: 0 0 8px;
  color: var(--color-text);
  font-size: 17px;
  font-weight: 700;
}

.mark-desc {
  margin: 0;
  color: var(--color-muted);
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}

.empty-msg {
  padding: 24px 0 8px;
  text-align: center;
  color: var(--color-muted);
}

.skeleton-card {
  height: 120px;
  border-radius: 14px;
  background: var(--color-bg);
  animation: shimmer 1.4s infinite;
}

@keyframes shimmer {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}

@media (max-width: 720px) {
  .page-header {
    flex-wrap: wrap;
  }

  .page-title {
    width: 100%;
  }

  .page-main {
    padding: 16px;
  }

  .search-row {
    flex-direction: column;
    align-items: stretch;
  }

  .result-head {
    flex-direction: column;
  }
}
</style>
