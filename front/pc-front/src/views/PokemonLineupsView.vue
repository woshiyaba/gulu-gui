<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchLineups } from '@/api/pokemon'
import { useTheme } from '@/composables/useTheme'
import type { Lineup } from '@/types'

const router = useRouter()
const { isDark, toggleTheme } = useTheme()

const loading = ref(false)
const error = ref('')
const lineups = ref<Lineup[]>([])
const sourceFilter = ref('')

const SOURCE_LABELS: Record<string, string> = {
  shining_contest: '闪耀大赛',
  open_battle: '露天对战',
  season_battle: '赛季对战',
  starlight_duel: '星光对决',
}

function sourceLabel(code: string): string {
  return SOURCE_LABELS[code] || code || '未分类'
}

async function loadLineups() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchLineups(sourceFilter.value || undefined)
    lineups.value = res.items
  } catch {
    error.value = '加载阵容失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  void loadLineups()
}

onMounted(() => {
  void loadLineups()
})
</script>

<template>
  <div class="lineups-page">
    <header class="page-header">
      <button class="back-btn" @click="router.push('/')">← 返回图鉴</button>
      <h1 class="page-title">精灵阵容推荐</h1>
      <button class="theme-btn" @click="toggleTheme">
        {{ isDark ? '切换浅色' : '夜间模式' }}
      </button>
    </header>

    <main class="page-main">
      <div class="filter-bar">
        <span class="filter-label">分类筛选</span>
        <select v-model="sourceFilter" class="filter-select" @change="onFilterChange">
          <option value="">全部</option>
          <option v-for="(label, code) in SOURCE_LABELS" :key="code" :value="code">{{ label }}</option>
        </select>
      </div>

      <div v-if="error" class="error-msg">{{ error }}</div>

      <div v-if="loading" class="loading-msg">加载中...</div>

      <div v-else-if="lineups.length === 0 && !error" class="empty-msg">暂无阵容数据</div>

      <div v-else class="lineup-list">
        <RouterLink
          v-for="lineup in lineups"
          :key="lineup.id"
          class="lineup-card"
          :to="`/lineups/${lineup.id}`"
        >
          <div class="lineup-head">
            <h2 class="lineup-title">{{ lineup.title || '未命名阵容' }}</h2>
            <span class="lineup-tag">{{ sourceLabel(lineup.source_type) }}</span>
          </div>

          <div class="member-row">
            <div
              v-for="m in lineup.members"
              :key="m.id"
              class="member-avatar"
              :title="m.pokemon_name"
            >
              <img v-if="m.pokemon_image" :src="m.pokemon_image" :alt="m.pokemon_name" />
              <span v-else class="avatar-placeholder">?</span>
              <span class="avatar-name">{{ m.pokemon_name }}</span>
            </div>
          </div>

          <div class="lineup-footer">
            <span class="lineup-count">{{ lineup.members.length }} 只精灵</span>
            <span class="view-detail">查看详情 →</span>
          </div>
        </RouterLink>
      </div>
    </main>
  </div>
</template>

<style scoped>
.lineups-page {
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

.back-btn,
.theme-btn {
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

.back-btn:hover {
  background: var(--color-hover);
}

.page-title {
  flex: 1;
  margin: 0;
  font-size: 22px;
  color: var(--color-accent);
}

.theme-btn {
  padding: 8px 16px;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
}

.theme-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.page-main {
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.filter-label {
  font-size: 14px;
  color: var(--color-muted);
}

.filter-select {
  padding: 8px 14px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 14px;
  outline: none;
  cursor: pointer;
}

.filter-select:focus {
  border-color: var(--color-accent);
}

.error-msg {
  margin-bottom: 20px;
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  color: #f87171;
}

.loading-msg,
.empty-msg {
  padding: 40px 0;
  text-align: center;
  color: var(--color-muted);
  font-size: 15px;
}

.lineup-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.lineup-card {
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.2s, transform 0.15s;
}

.lineup-card:hover {
  border-color: var(--color-accent);
  transform: translateY(-2px);
}

.lineup-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px 8px;
}

.lineup-title {
  margin: 0;
  font-size: 17px;
  color: var(--color-text);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lineup-tag {
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  background: rgba(64, 158, 255, 0.12);
  color: var(--color-accent);
  flex-shrink: 0;
}

.member-row {
  display: flex;
  gap: 8px;
  padding: 10px 20px 12px;
  flex-wrap: wrap;
}

.member-avatar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
}

.member-avatar img {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  object-fit: contain;
}

.avatar-placeholder {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  display: grid;
  place-items: center;
  font-size: 18px;
  color: var(--color-muted);
}

.avatar-name {
  font-size: 11px;
  color: var(--color-muted);
  max-width: 52px;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lineup-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px 14px;
  margin-top: auto;
}

.lineup-count {
  font-size: 13px;
  color: var(--color-muted);
}

.view-detail {
  font-size: 13px;
  color: var(--color-accent);
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

  .lineup-list {
    grid-template-columns: 1fr;
  }

  .member-avatar img,
  .avatar-placeholder {
    width: 40px;
    height: 40px;
  }
}
</style>
