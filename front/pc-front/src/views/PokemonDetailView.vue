<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchPokemonDetail } from '@/api/pokemon'
import { useTheme } from '@/composables/useTheme'
import type { PokemonDetail } from '@/types'

const route = useRoute()
const router = useRouter()
const { isDark, toggleTheme } = useTheme()

const pokemon = ref<PokemonDetail | null>(null)
const loading = ref(true)
const error = ref('')

// 种族值配置：标签、最大值（用于进度条百分比）
const STAT_CONFIGS = [
  { key: 'hp',      label: 'HP',   max: 500, color: '#34d399' },
  { key: 'atk',     label: '物攻', max: 500, color: '#f87171' },
  { key: 'matk',    label: '魔攻', max: 500, color: '#c084fc' },
  { key: 'def_val', label: '物防', max: 500, color: '#60a5fa' },
  { key: 'mdef',    label: '魔防', max: 500, color: '#818cf8' },
  { key: 'spd',     label: '速度', max: 500, color: '#fbbf24' },
] as const

function statPercent(val: number, max: number) {
  return Math.min(100, Math.round((val / max) * 100))
}

async function load(name: string) {
  loading.value = true
  error.value = ''
  try {
    pokemon.value = await fetchPokemonDetail(name)
  } catch {
    error.value = '加载失败，精灵不存在或后端未启动'
  } finally {
    loading.value = false
  }
}

onMounted(() => load(route.params.name as string))
watch(() => route.params.name, (n) => n && load(n as string))
</script>

<template>
  <div class="detail-page">
    <!-- 顶部导航 -->
    <header class="detail-header">
      <button class="back-btn" @click="router.back()">← 返回图鉴</button>
      <h1 class="header-title" v-if="pokemon">{{ pokemon.name }}</h1>
      <button class="theme-btn" @click="toggleTheme">
        {{ isDark ? '切换浅色' : '夜间模式' }}
      </button>
    </header>

    <!-- 加载中 -->
    <div v-if="loading" class="center-msg">加载中...</div>

    <!-- 错误 -->
    <div v-else-if="error" class="error-msg">{{ error }}</div>

    <!-- 详情内容 -->
    <main v-else-if="pokemon" class="detail-main">

      <!-- ① 基础信息卡 -->
      <section class="card info-card">
        <div class="pokemon-avatar">
          <img v-if="pokemon.image_url" :src="pokemon.image_url" :alt="pokemon.name" class="avatar-img" />
          <div v-else class="avatar-placeholder">?</div>
        </div>
        <div class="info-meta">
          <div class="info-no">{{ pokemon.no }}</div>
          <div class="info-name">{{ pokemon.name }}</div>
          <div class="info-attrs">
            <span v-for="a in pokemon.attributes" :key="a.attr_name" class="attr-tag">
              <img v-if="a.attr_image" :src="a.attr_image" :alt="a.attr_name" class="attr-icon" />
              {{ a.attr_name }}
            </span>
          </div>
          <div class="info-tags">
            <span v-if="pokemon.type_name" class="badge badge-type">{{ pokemon.type_name }}</span>
            <span v-if="pokemon.form_name" class="badge badge-form">{{ pokemon.form_name }}</span>
          </div>
          <div class="obtain-method">
            <span class="obtain-label">获取方式</span>
            <span class="obtain-value">{{ pokemon.obtain_method || '暂无数据' }}</span>
          </div>
        </div>
      </section>

      <!-- ② 种族值 -->
      <section class="card">
        <h2 class="section-title">种族值</h2>
        <div class="stats-list">
          <div
            v-for="cfg in STAT_CONFIGS"
            :key="cfg.key"
            class="stat-row"
          >
            <span class="stat-label">{{ cfg.label }}</span>
            <div class="stat-bar-wrap">
              <div
                class="stat-bar"
                :style="{
                  width: statPercent(pokemon.stats[cfg.key], cfg.max) + '%',
                  background: cfg.color,
                }"
              ></div>
            </div>
            <span class="stat-val">{{ pokemon.stats[cfg.key] }}</span>
          </div>
        </div>
      </section>

      <!-- ③ 特性 -->
      <section v-if="pokemon.trait.name" class="card">
        <h2 class="section-title">特性</h2>
        <div class="trait-name">{{ pokemon.trait.name }}</div>
        <div class="trait-desc">{{ pokemon.trait.desc || '暂无描述' }}</div>
      </section>

      <!-- ④ 属性克制关系 -->
      <section class="card">
        <h2 class="section-title">属性克制</h2>
        <div class="restrain-grid">
          <div class="restrain-group" v-if="pokemon.restrain.strong_against.length">
            <div class="restrain-label restrain-strong">克制（攻击有效）</div>
            <div class="restrain-tags">
              <span v-for="a in pokemon.restrain.strong_against" :key="a" class="rtag rtag-strong">{{ a }}</span>
            </div>
          </div>
          <div class="restrain-group" v-if="pokemon.restrain.weak_against.length">
            <div class="restrain-label restrain-weak">被克制（受到更多伤害）</div>
            <div class="restrain-tags">
              <span v-for="a in pokemon.restrain.weak_against" :key="a" class="rtag rtag-weak">{{ a }}</span>
            </div>
          </div>
          <div class="restrain-group" v-if="pokemon.restrain.resist.length">
            <div class="restrain-label restrain-resist">抵抗（受到较少伤害）</div>
            <div class="restrain-tags">
              <span v-for="a in pokemon.restrain.resist" :key="a" class="rtag rtag-resist">{{ a }}</span>
            </div>
          </div>
          <div class="restrain-group" v-if="pokemon.restrain.resisted.length">
            <div class="restrain-label restrain-resisted">被抵抗（攻击效果差）</div>
            <div class="restrain-tags">
              <span v-for="a in pokemon.restrain.resisted" :key="a" class="rtag rtag-resisted">{{ a }}</span>
            </div>
          </div>
          <div
            v-if="!pokemon.restrain.strong_against.length && !pokemon.restrain.weak_against.length
              && !pokemon.restrain.resist.length && !pokemon.restrain.resisted.length"
            class="no-data"
          >暂无克制数据</div>
        </div>
      </section>

      <!-- ⑤ 技能列表 -->
      <section class="card skills-card">
        <h2 class="section-title">技能（{{ pokemon.skills.length }} 个）</h2>
        <div v-if="pokemon.skills.length === 0" class="no-data">暂无技能数据</div>
        <table v-else class="skill-table">
          <thead>
            <tr>
              <th>技能名</th>
              <th>属性</th>
              <th>类型</th>
              <th>威力</th>
              <th>消耗</th>
              <th>描述</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="sk in pokemon.skills" :key="sk.name">
              <td
                class="skill-name"
                tabindex="0"
                :data-skill-desc="(sk.desc && String(sk.desc).trim()) ? String(sk.desc).trim() : '暂无描述'"
              >
                <img v-if="sk.icon" :src="sk.icon" :alt="sk.name" class="skill-icon" />
                {{ sk.name }}
              </td>
              <td><span class="skill-attr">{{ sk.attr || '—' }}</span></td>
              <td><span class="skill-type" :class="'type-' + sk.type">{{ sk.type || '—' }}</span></td>
              <td class="skill-num">{{ sk.power ?? '—' }}</td>
              <td class="skill-num">{{ sk.consume ?? '—' }}</td>
              <td class="skill-desc">{{ sk.desc || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </section>

    </main>
  </div>
</template>

<style scoped>
.detail-page {
  min-height: 100vh;
  background: var(--color-bg);
}

/* 顶部导航 */
.detail-header {
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

.back-btn {
  padding: 6px 16px;
  border: 2px solid var(--color-accent);
  border-radius: 20px;
  background: transparent;
  color: var(--color-accent);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.back-btn:hover {
  background: var(--color-accent);
  color: #fff;
}

.header-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}

.theme-btn {
  margin-left: auto;
  padding: 7px 16px;
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

/* 主体 */
.detail-main {
  max-width: 860px;
  margin: 0 auto;
  padding: 24px 20px 60px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.center-msg {
  text-align: center;
  padding: 100px 0;
  color: var(--color-muted);
}

.error-msg {
  max-width: 860px;
  margin: 40px auto;
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #f87171;
  font-size: 14px;
}

/* 通用卡片 */
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: 20px 24px;
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-accent);
  margin-bottom: 16px;
}

.no-data {
  color: var(--color-muted);
  font-size: 13px;
  padding: 8px 0;
}

/* ① 基础信息 */
.info-card {
  display: flex;
  align-items: center;
  gap: 28px;
}

.pokemon-avatar {
  flex-shrink: 0;
  width: 140px;
  height: 140px;
  background: var(--color-img-bg);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-img {
  max-width: 130px;
  max-height: 130px;
  object-fit: contain;
}

.avatar-placeholder {
  font-size: 60px;
  color: var(--color-muted);
}

.info-no {
  font-size: 12px;
  color: var(--color-muted);
  margin-bottom: 4px;
}

.info-name {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 10px;
}

.info-attrs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.attr-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  background: var(--color-tag-bg);
  border-radius: 12px;
  font-size: 12px;
  color: var(--color-text);
}

.attr-icon {
  width: 16px;
  height: 16px;
  object-fit: contain;
}

.info-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.obtain-method {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  font-size: 13px;
  line-height: 1.6;
}

.obtain-label {
  color: var(--color-muted);
}

.obtain-value {
  color: var(--color-text);
}

.badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
}

.badge-type {
  background: rgba(99, 102, 241, 0.15);
  color: #818cf8;
}

.badge-form {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
}

/* ② 种族值 */
.stats-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-row {
  display: grid;
  grid-template-columns: 40px 1fr 48px;
  align-items: center;
  gap: 12px;
}

.stat-label {
  font-size: 12px;
  color: var(--color-muted);
  text-align: right;
}

.stat-bar-wrap {
  background: var(--color-border);
  border-radius: 4px;
  height: 10px;
  overflow: hidden;
}

.stat-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}

.stat-val {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  text-align: right;
}

/* ③ 特性 */
.trait-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 8px;
}

.trait-desc {
  font-size: 13px;
  color: var(--color-muted);
  line-height: 1.6;
}

/* ④ 克制关系 */
.restrain-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.restrain-group {}

.restrain-label {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
}

.restrain-strong  { color: #34d399; }
.restrain-weak    { color: #f87171; }
.restrain-resist  { color: #60a5fa; }
.restrain-resisted{ color: #fbbf24; }

.restrain-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.rtag {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 12px;
}

.rtag-strong   { background: rgba(52, 211, 153, 0.15); color: #34d399; }
.rtag-weak     { background: rgba(248, 113, 113, 0.15); color: #f87171; }
.rtag-resist   { background: rgba(96, 165, 250, 0.15); color: #60a5fa; }
.rtag-resisted { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }

/* ⑤ 技能表格 */
.skill-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.skill-table th {
  text-align: left;
  padding: 6px 10px;
  color: var(--color-muted);
  border-bottom: 1px solid var(--color-border);
  font-weight: 600;
  white-space: nowrap;
}

.skill-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--color-table-divider);
  color: var(--color-text);
  vertical-align: top;
}

.skill-table tr:last-child td {
  border-bottom: none;
}

.skill-table tr:hover td {
  background: var(--color-hover);
}

.skill-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  white-space: nowrap;
}

.skill-icon {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

.skill-attr {
  display: inline-block;
  padding: 1px 6px;
  background: var(--color-tag-bg);
  border-radius: 8px;
  font-size: 11px;
}

.skill-type {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 8px;
  font-size: 11px;
}

.type-物攻 { background: rgba(248, 113, 113, 0.15); color: #f87171; }
.type-魔攻 { background: rgba(192, 132, 252, 0.15); color: #c084fc; }
.type-状态 { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
.type-防御 { background: rgba(96, 165, 250, 0.15); color: #60a5fa; }

.skill-num {
  text-align: center;
  color: var(--color-muted);
}

.skill-desc {
  color: var(--color-muted);
  font-size: 12px;
  min-width: 120px;
}

@media (max-width: 600px) {
  .detail-header {
    flex-wrap: wrap;
  }

  .theme-btn {
    margin-left: 0;
  }

  .info-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .detail-main {
    padding-left: 12px;
    padding-right: 12px;
  }

  .card {
    padding: 14px 14px;
  }

  .section-title {
    margin-bottom: 10px;
  }

  .skill-table th:nth-child(6),
  .skill-table td:nth-child(6) {
    display: none;
  }

  .skill-table {
    font-size: 11px;
  }

  .skill-table th,
  .skill-table td {
    padding: 5px 6px;
  }

  .skill-attr,
  .skill-type {
    font-size: 10px;
    padding: 1px 4px;
    white-space: nowrap;
  }

  /* 窄屏隐藏描述列时：聚焦技能名显示黑底白字说明（纯 CSS，data-skill-desc） */
  .skills-card {
    overflow: visible;
  }

  .skill-table,
  .skill-table tbody,
  .skill-table tr,
  .skill-table td {
    overflow: visible;
  }

  .skill-name {
    position: relative;
    cursor: default;
  }

  .skill-name:focus {
    outline: none;
  }

  .skill-name:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }

  .skill-name:focus::after,
  .skill-name:focus-visible::after {
    content: attr(data-skill-desc);
    position: absolute;
    left: 0;
    top: 100%;
    z-index: 50;
    margin-top: 4px;
    min-width: min(280px, calc(100vw - 24px));
    max-width: min(480px, calc(100vw - 16px));
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 400;
    line-height: 1.5;
    white-space: normal;
    word-break: break-word;
    color: #fff;
    background: #141414;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
    pointer-events: none;
  }
}
</style>
