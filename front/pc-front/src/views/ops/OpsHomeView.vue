<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  fetchOpsMe,
  fetchOpsPokemon,
  fetchOpsSkills,
  fetchOpsUsers,
  fetchOpsDicts,
  fetchOpsBanners,
  fetchOpsPokemonLineups,
  fetchOpsAuditLogs,
  type OpsAuditLogItem,
  type OpsUser,
} from '@/api/ops'

const router = useRouter()
const user = ref<OpsUser | null>(null)
const loading = ref(true)
const stats = reactive({
  pokemon: 0,
  skills: 0,
  users: 0,
  dicts: 0,
  banners: 0,
  lineups: 0,
})
const recentLogs = ref<OpsAuditLogItem[]>([])
const error = ref('')

const greetings = ['你好', '上午好', '下午好', '晚上好']
const greet = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return greetings[0]
  if (h < 12) return greetings[1]
  if (h < 18) return greetings[2]
  return greetings[3]
})

const resourceLabels: Record<string, string> = {
  pokemon: '精灵',
  skill: '技能',
  skill_stone: '技能石',
  banner: 'Banner',
  personality: '性格',
  dict: '字典',
  user: '用户',
  mark: '印记',
  resonance_magic: '共鸣魔法',
  pokemon_lineup: '阵容',
  pokemon_mark: '名词解释',
  pokemon_filter_option: '筛选项',
}

const quickLinks = [
  { label: '精灵维护', to: '/ops/pokemon', desc: '精灵数据的增删改查' },
  { label: '技能维护', to: '/ops/skills', desc: '技能数据的维护管理' },
  { label: '字典维护', to: '/ops/dicts', desc: '系统字典配置' },
  { label: 'Banner管理', to: '/ops/banners', desc: '首页Banner配置' },
  { label: '阵容管理', to: '/ops/pokemon-lineups', desc: '精灵阵容配置' },
  { label: '用户管理', to: '/ops/users', desc: '运维用户管理' },
]

async function loadStats() {
  try {
    const [pokemonRes, skillsRes, usersRes, dictsRes, bannersRes, lineupsRes] = await Promise.all([
      fetchOpsPokemon({ page: 1, page_size: 1 }),
      fetchOpsSkills({ page: 1, page_size: 1 }),
      fetchOpsUsers(),
      fetchOpsDicts({ page: 1, page_size: 1 }),
      fetchOpsBanners({ page: 1, page_size: 1 }),
      fetchOpsPokemonLineups({ page: 1, page_size: 1 }),
    ])
    stats.pokemon = pokemonRes.total
    stats.skills = skillsRes.total
    stats.users = usersRes.items.length
    stats.dicts = dictsRes.total
    stats.banners = bannersRes.total
    stats.lineups = lineupsRes.total
  } catch {
    error.value = '部分数据加载失败'
  }
}

async function loadRecentLogs() {
  try {
    const res = await fetchOpsAuditLogs({ page: 1, page_size: 10 })
    recentLogs.value = res.items
  } catch {
    // silent
  }
}

function formatTime(ts: string) {
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function goTo(to: string) {
  void router.push(to)
}

onMounted(async () => {
  try {
    user.value = await fetchOpsMe()
  } catch {
    // not logged in
  }
  await Promise.all([loadStats(), loadRecentLogs()])
  loading.value = false
})
</script>

<template>
  <section v-if="loading" class="ops-loading">加载中...</section>

  <section v-else class="ops-dashboard">
    <!-- Welcome -->
    <div class="ops-card-padded ops-welcome">
      <div class="ops-welcome-text">
        <h1>{{ greet }}，{{ (user?.nickname || user?.username || '用户') }}</h1>
        <p>今天是 {{ new Date().toLocaleDateString('zh-CN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }) }} · 运营维护平台</p>
      </div>
      <div class="ops-welcome-actions">
        <button class="ops-btn ops-btn-primary" @click="goTo('/ops/pokemon')">精灵维护</button>
        <button class="ops-btn ops-btn-secondary" @click="goTo('/ops/dicts')">字典维护</button>
      </div>
    </div>

    <div class="ops-dashboard-body">
      <!-- Stats -->
      <div class="ops-stats-grid">
        <div class="ops-stat-card" @click="goTo('/ops/pokemon')">
          <span class="ops-stat-icon ops-stat-icon--accent">P</span>
          <span class="ops-stat-value">{{ stats.pokemon }}</span>
          <span class="ops-stat-label">精灵总数</span>
        </div>
        <div class="ops-stat-card" @click="goTo('/ops/skills')">
          <span class="ops-stat-icon ops-stat-icon--green">S</span>
          <span class="ops-stat-value">{{ stats.skills }}</span>
          <span class="ops-stat-label">技能总数</span>
        </div>
        <div class="ops-stat-card" @click="goTo('/ops/dicts')">
          <span class="ops-stat-icon ops-stat-icon--orange">D</span>
          <span class="ops-stat-value">{{ stats.dicts }}</span>
          <span class="ops-stat-label">字典条目</span>
        </div>
        <div class="ops-stat-card" @click="goTo('/ops/pokemon-lineups')">
          <span class="ops-stat-icon ops-stat-icon--purple">L</span>
          <span class="ops-stat-value">{{ stats.lineups }}</span>
          <span class="ops-stat-label">精灵阵容</span>
        </div>
        <div class="ops-stat-card" @click="goTo('/ops/banners')">
          <span class="ops-stat-icon ops-stat-icon--pink">B</span>
          <span class="ops-stat-value">{{ stats.banners }}</span>
          <span class="ops-stat-label">Banner</span>
        </div>
        <div class="ops-stat-card" @click="goTo('/ops/users')">
          <span class="ops-stat-icon ops-stat-icon--teal">U</span>
          <span class="ops-stat-value">{{ stats.users }}</span>
          <span class="ops-stat-label">运维用户</span>
        </div>
      </div>

      <div class="ops-dashboard-bottom">
        <!-- Recent activity -->
        <div class="ops-card-padded ops-section--logs">
          <h2 class="ops-section-title">最近操作</h2>
          <div v-if="recentLogs.length === 0" class="ops-empty">
            <strong>暂无操作记录</strong>
          </div>
          <div v-else class="ops-log-list">
            <div v-for="log in recentLogs" :key="log.id" class="ops-log-item">
              <span class="ops-log-badge" :class="`ops-log-badge--${log.action}`">{{ log.action }}</span>
              <span class="ops-log-user">{{ log.nickname || log.username }}</span>
              <span class="ops-log-resource">{{ resourceLabels[log.resource_type] || log.resource_type }}</span>
              <span v-if="log.resource_id" class="ops-log-id"><code>#{{ log.resource_id }}</code></span>
              <span class="ops-log-time">{{ formatTime(log.created_at) }}</span>
            </div>
          </div>
        </div>

        <!-- Quick links -->
        <div class="ops-card-padded ops-section--links">
          <h2 class="ops-section-title">快捷入口</h2>
          <div class="ops-link-list">
            <button v-for="link in quickLinks" :key="link.to" class="ops-link-item" @click="goTo(link.to)">
              <span class="ops-link-label">{{ link.label }}</span>
              <span class="ops-link-desc">{{ link.desc }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.ops-dashboard {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.ops-welcome {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: linear-gradient(135deg, var(--ops-accent) 0%, oklch(52% 0.2 255) 100%);
  border: none;
  border-radius: var(--ops-radius-md);
  color: #fff;
  padding: 18px 24px;
  cursor: default;
  flex-shrink: 0;
}
.ops-welcome-text h1 {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.01em;
  margin-bottom: 2px;
}
.ops-welcome-text p {
  font-size: 13px;
  opacity: 0.82;
}
.ops-welcome-actions { display: flex; gap: 8px; flex-shrink: 0; }
.ops-welcome-actions .ops-btn { border-color: rgba(255,255,255,0.25); }
.ops-welcome-actions .ops-btn-primary { background: rgba(255,255,255,0.2); border-color: rgba(255,255,255,0.35); color: #fff; }
.ops-welcome-actions .ops-btn-primary:hover { background: rgba(255,255,255,0.3); }
.ops-welcome-actions .ops-btn-secondary { background: transparent; color: #fff; }
.ops-welcome-actions .ops-btn-secondary:hover { background: rgba(255,255,255,0.12); }

.ops-dashboard-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 14px;
  min-height: 0;
}

.ops-stats-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  flex-shrink: 0;
}
.ops-stat-card {
  background: var(--ops-surface);
  border: 1px solid var(--ops-border);
  border-radius: var(--ops-radius-sm);
  padding: 14px 14px 12px;
  display: grid;
  gap: 3px;
  cursor: pointer;
  transition: border-color 0.15s ease;
}
.ops-stat-card:hover { border-color: var(--ops-accent); }
.ops-stat-icon {
  width: 28px;
  height: 28px;
  border-radius: 4px;
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 12px;
  color: #fff;
  margin-bottom: 4px;
}
.ops-stat-icon--accent { background: var(--ops-accent); }
.ops-stat-icon--green  { background: var(--ops-success); }
.ops-stat-icon--orange { background: var(--ops-warning); }
.ops-stat-icon--purple { background: oklch(55% 0.18 290); }
.ops-stat-icon--pink   { background: oklch(55% 0.16 350); }
.ops-stat-icon--teal   { background: oklch(55% 0.14 195); }
.ops-stat-value {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.1;
  color: var(--ops-text);
}
.ops-stat-label {
  font-size: var(--ops-font-size-xs);
  color: var(--ops-muted);
}

.ops-dashboard-bottom {
  flex: 1;
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 14px;
  min-height: 0;
}
.ops-section--logs { display: flex; flex-direction: column; min-height: 0; }
.ops-section--logs .ops-section-title { margin-bottom: 0; flex-shrink: 0; }
.ops-section--links { display: flex; flex-direction: column; min-height: 0; }
.ops-section--links .ops-section-title { margin-bottom: 12px; flex-shrink: 0; }

.ops-log-list {
  flex: 1;
  overflow-y: auto;
  margin-top: 8px;
  display: flex;
  flex-direction: column;
}
.ops-log-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 0;
  border-bottom: 1px solid var(--ops-border-light);
  font-size: var(--ops-font-size-sm);
}
.ops-log-item:last-child { border-bottom: none; }
.ops-log-badge {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 7px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  flex-shrink: 0;
}
.ops-log-badge--create { background: var(--ops-success-light); color: var(--ops-success); }
.ops-log-badge--update { background: var(--ops-accent-light); color: var(--ops-accent); }
.ops-log-badge--delete { background: var(--ops-danger-light); color: var(--ops-danger); }
.ops-log-user { color: var(--ops-text); font-weight: 500; white-space: nowrap; }
.ops-log-resource { color: var(--ops-text-secondary); }
.ops-log-id code { font-size: 10px; color: var(--ops-muted); }
.ops-log-time { margin-left: auto; color: var(--ops-muted); white-space: nowrap; font-size: var(--ops-font-size-xs); }

.ops-link-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.ops-link-item {
  display: grid;
  gap: 1px;
  padding: 10px;
  border: 1px solid var(--ops-border-light);
  border-radius: var(--ops-radius-sm);
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.12s ease;
}
.ops-link-item:hover { border-color: var(--ops-accent); }
.ops-link-label { font-size: 13px; font-weight: 600; color: var(--ops-text); }
.ops-link-desc { font-size: 11px; color: var(--ops-muted); }

@media (max-width: 1100px) {
  .ops-stats-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 720px) {
  .ops-stats-grid { grid-template-columns: repeat(2, 1fr); }
  .ops-dashboard-bottom { grid-template-columns: 1fr; }
  .ops-welcome { flex-direction: column; align-items: flex-start; }
  .ops-link-list { grid-template-columns: 1fr; }
}
</style>
