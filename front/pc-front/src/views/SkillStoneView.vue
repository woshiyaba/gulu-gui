<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchSkillStones } from '@/api/pokemon'
import { useTheme } from '@/composables/useTheme'
import type { SkillStone } from '@/types'

const router = useRouter()
const { isDark, toggleTheme } = useTheme()

const keyword = ref('')
const loading = ref(false)
const error = ref('')
const skillStones = ref<SkillStone[]>([])
const total = ref(0)
const hasLoaded = ref(false)

const summaryText = computed(() => {
  if (!hasLoaded.value) return ''
  if (keyword.value.trim()) {
    return `关键词“${keyword.value.trim()}”共匹配到 ${total.value} 条技能石记录。`
  }
  return `当前共收录 ${total.value} 条技能石记录。`
})

async function loadSkillStones() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchSkillStones({
      skill_name: keyword.value || undefined,
    })
    skillStones.value = res.items
    total.value = res.total
    hasLoaded.value = true
  } catch {
    error.value = '查询失败，请确认后端服务已启动且技能石数据已导入'
    skillStones.value = []
    total.value = 0
    hasLoaded.value = true
  } finally {
    loading.value = false
  }
}

function onSearch() {
  void loadSkillStones()
}

function onReset() {
  keyword.value = ''
  void loadSkillStones()
}

onMounted(() => {
  void loadSkillStones()
})
</script>

<template>
  <div class="skill-stone-page">
    <header class="page-header">
      <button class="back-btn" @click="router.push('/')">← 返回图鉴</button>
      <h1 class="page-title">技能石查询</h1>
      <button class="theme-btn" @click="toggleTheme">
        {{ isDark ? '切换浅色' : '夜间模式' }}
      </button>
    </header>

    <main class="page-main">
      <section class="card search-card">
        <h2 class="section-title">按技能名查询</h2>
        <p class="helper-text">不输入技能名时会返回全部技能石，输入后按技能名关键词模糊查询。</p>

        <div class="search-row">
          <input
            v-model="keyword"
            class="search-input"
            type="text"
            placeholder="例如：光、龙、光合作用"
            @keyup.enter="onSearch"
          />
          <button class="action-btn primary-btn" :disabled="loading" @click="onSearch">
            {{ loading ? '查询中...' : '开始查询' }}
          </button>
          <button class="action-btn secondary-btn" :disabled="loading" @click="onReset">
            重置
          </button>
        </div>
      </section>

      <div v-if="error" class="error-msg">{{ error }}</div>

      <section v-if="hasLoaded" class="card result-card">
        <div class="result-head">
          <h2 class="section-title">查询结果</h2>
          <span class="result-summary">{{ summaryText }}</span>
        </div>

        <div v-if="loading" class="skeleton-grid">
          <div v-for="n in 8" :key="n" class="skeleton-card"></div>
        </div>

        <div v-else-if="skillStones.length === 0" class="empty-msg">
          没有找到匹配的技能石记录
        </div>

        <div v-else class="stone-grid">
          <article v-for="item in skillStones" :key="item.skill_name" class="stone-card">
            <div class="stone-icon-wrap">
              <img
                v-if="item.icon"
                :src="item.icon"
                :alt="item.skill_name"
                class="stone-icon"
                loading="lazy"
              />
              <div v-else class="stone-icon-placeholder">?</div>
            </div>
            <div class="stone-body">
              <h3 class="stone-name">{{ item.skill_name }}</h3>
              <p class="stone-method">{{ item.obtain_method }}</p>
            </div>
          </article>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.skill-stone-page {
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

.primary-btn {
  border-color: var(--color-accent);
  color: var(--color-accent);
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

.stone-grid,
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.stone-card {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: var(--color-bg);
  box-shadow: var(--color-shadow);
}

.stone-icon-wrap {
  width: 72px;
  height: 72px;
  border-radius: 14px;
  background: var(--color-img-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}

.stone-icon {
  width: 56px;
  height: 56px;
  object-fit: contain;
}

.stone-icon-placeholder {
  font-size: 28px;
  color: var(--color-muted);
}

.stone-body {
  min-width: 0;
}

.stone-name {
  margin: 0 0 8px;
  color: var(--color-text);
  font-size: 17px;
  font-weight: 700;
}

.stone-method {
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
