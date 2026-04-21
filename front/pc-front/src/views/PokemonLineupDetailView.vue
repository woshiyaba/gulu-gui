<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchLineupDetail } from '@/api/pokemon'
import { useTheme } from '@/composables/useTheme'
import type { Lineup, LineupMember } from '@/types'

const route = useRoute()
const router = useRouter()
const { isDark, toggleTheme } = useTheme()

const loading = ref(false)
const error = ref('')
const lineup = ref<Lineup | null>(null)

const SOURCE_LABELS: Record<string, string> = {
  shining_contest: '闪耀大赛',
  open_battle: '露天对战',
  season_battle: '赛季对战',
  starlight_duel: '星光对决',
}

function sourceLabel(code: string): string {
  return SOURCE_LABELS[code] || code || '未分类'
}

function skills(m: LineupMember) {
  const list = []
  if (m.skill_1_id) list.push({ name: m.skill_1_name, image: m.skill_1_image })
  if (m.skill_2_id) list.push({ name: m.skill_2_name, image: m.skill_2_image })
  if (m.skill_3_id) list.push({ name: m.skill_3_name, image: m.skill_3_image })
  if (m.skill_4_id) list.push({ name: m.skill_4_name, image: m.skill_4_image })
  return list
}

async function loadDetail() {
  const id = Number(route.params.id)
  if (!id) {
    error.value = '无效的阵容 ID'
    return
  }
  loading.value = true
  error.value = ''
  try {
    lineup.value = await fetchLineupDetail(id)
  } catch {
    error.value = '加载阵容详情失败，可能该阵容不存在或未启用'
  } finally {
    loading.value = false
  }
}

watch(() => route.params.id, () => {
  void loadDetail()
})

onMounted(() => {
  void loadDetail()
})
</script>

<template>
  <div class="detail-page">
    <header class="page-header">
      <button class="back-btn" @click="router.push('/lineups')">← 返回阵容列表</button>
      <h1 class="page-title">{{ lineup?.title || '阵容详情' }}</h1>
      <button class="theme-btn" @click="toggleTheme">
        {{ isDark ? '切换浅色' : '夜间模式' }}
      </button>
    </header>

    <main class="page-main">
      <div v-if="error" class="error-msg">{{ error }}</div>

      <div v-if="loading" class="loading-msg">加载中...</div>

      <template v-else-if="lineup">
        <section class="lineup-meta card">
          <div class="meta-row">
            <span class="meta-tag">{{ sourceLabel(lineup.source_type) }}</span>
            <span class="meta-count">{{ lineup.members.length }} 只精灵</span>
          </div>
          <p v-if="lineup.lineup_desc" class="lineup-desc">{{ lineup.lineup_desc }}</p>
        </section>

        <section class="members-grid">
          <div v-for="m in lineup.members" :key="m.id" class="member-card card">
            <div class="member-head">
              <RouterLink
                :to="`/pokemon/${encodeURIComponent(m.pokemon_name)}`"
                class="member-img-link"
              >
                <img v-if="m.pokemon_image" :src="m.pokemon_image" class="member-img" :alt="m.pokemon_name" />
                <div v-else class="member-img-placeholder">?</div>
              </RouterLink>
              <div class="member-info">
                <RouterLink
                  :to="`/pokemon/${encodeURIComponent(m.pokemon_name)}`"
                  class="member-name"
                >
                  {{ m.pokemon_name }}
                </RouterLink>
                <div class="member-tags">
                  <span v-if="m.bloodline_label" class="tag bloodline">{{ m.bloodline_label }}</span>
                  <span v-if="m.personality_name_zh" class="tag personality">{{ m.personality_name_zh }}</span>
                </div>
              </div>
            </div>

            <div v-if="skills(m).length" class="skills-section">
              <h3 class="section-label">技能</h3>
              <div class="skill-list">
                <div v-for="(sk, si) in skills(m)" :key="si" class="skill-chip">
                  <img v-if="sk.image" :src="sk.image" class="skill-icon" alt="" />
                  <span>{{ sk.name }}</span>
                </div>
              </div>
            </div>

            <p v-if="m.member_desc" class="member-desc">{{ m.member_desc }}</p>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.detail-page {
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

.error-msg {
  margin-bottom: 20px;
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  color: #f87171;
}

.loading-msg {
  padding: 40px 0;
  text-align: center;
  color: var(--color-muted);
  font-size: 15px;
}

.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: 20px;
}

.lineup-meta {
  margin-bottom: 20px;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.meta-tag {
  padding: 3px 12px;
  border-radius: 12px;
  font-size: 13px;
  background: rgba(64, 158, 255, 0.12);
  color: var(--color-accent);
}

.meta-count {
  font-size: 14px;
  color: var(--color-muted);
}

.lineup-desc {
  margin: 0;
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text);
  white-space: pre-wrap;
}

.members-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.member-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.member-head {
  display: flex;
  align-items: center;
  gap: 14px;
}

.member-img-link {
  flex-shrink: 0;
}

.member-img {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  object-fit: contain;
}

.member-img-placeholder {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  display: grid;
  place-items: center;
  font-size: 24px;
  color: var(--color-muted);
}

.member-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.member-name {
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text);
  text-decoration: none;
  transition: color 0.15s;
}

.member-name:hover {
  color: var(--color-accent);
}

.member-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tag {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
}

.tag.bloodline {
  background: rgba(245, 108, 108, 0.12);
  color: #f56c6c;
}

.tag.personality {
  background: rgba(103, 194, 58, 0.12);
  color: #67c23a;
}

.skills-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.section-label {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-muted);
}

.skill-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 12px;
  border-radius: 14px;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  font-size: 13px;
  color: var(--color-text);
}

.skill-icon {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  object-fit: contain;
}

.member-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--color-muted);
  white-space: pre-wrap;
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

  .members-grid {
    grid-template-columns: 1fr;
  }

  .member-img {
    width: 52px;
    height: 52px;
  }

  .member-img-placeholder {
    width: 52px;
    height: 52px;
  }
}
</style>
