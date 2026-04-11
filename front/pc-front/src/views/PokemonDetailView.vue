<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchPokemonDetail, fetchPokemonEvolutionChain } from '@/api/pokemon'
import { useTheme } from '@/composables/useTheme'
import type { PokemonDetail, PokemonEvolutionChain } from '@/types'

const route = useRoute()
const router = useRouter()
const { isDark, toggleTheme } = useTheme()

const pokemon = ref<PokemonDetail | null>(null)
const evolutionChain = ref<PokemonEvolutionChain | null>(null)
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

/** 部分浏览器点击 table 单元格不会自动 focus，显式 focus 才能让 :focus::after 浮层出现 */
function focusSkillCell(ev: MouseEvent) {
  const el = ev.currentTarget
  if (el instanceof HTMLElement) el.focus()
}

function isCurrentEvolutionItem(name: string) {
  return pokemon.value?.name === name
}

async function goToEvolution(name: string) {
  if (String(route.params.name || '') === name) return
  await router.push(`/pokemon/${encodeURIComponent(name)}`)
}

async function load(name: string) {
  loading.value = true
  error.value = ''
  try {
    const [detail, chain] = await Promise.all([
      fetchPokemonDetail(name),
      fetchPokemonEvolutionChain(name),
    ])
    pokemon.value = detail
    evolutionChain.value = chain
  } catch {
    pokemon.value = null
    evolutionChain.value = null
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
      <div class="detail-content">
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
          <div v-if="pokemon.egg_groups?.length" class="egg-groups">
            <span class="egg-label">蛋组</span>
            <span v-for="g in pokemon.egg_groups" :key="g" class="badge badge-egg">{{ g }}</span>
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

      <!-- ④ 受击倍率表（按属性.json 矩阵，双属性相乘） -->
      <section v-if="pokemon.defensive_type_chart?.cells?.length" class="card">
        <h2 class="section-title">受击倍率</h2>
        <p class="type-chart-hint">
          精灵
          <span class="type-chart-def">{{ pokemon.defensive_type_chart.defender_attrs.join(' + ') }}</span>
          受到各「进攻招式属性」技能时的伤害倍率；
        </p>
        <!-- 宽屏：横向表格；窄屏：两排网格，无需左右滑动 -->
        <div class="type-chart-scroll type-chart--desktop">
          <table class="type-chart-table">
            <thead>
              <tr>
                <th class="tc-corner">进攻招式属性</th>
                <th
                  v-for="c in pokemon.defensive_type_chart.cells"
                  :key="c.attacker_attr"
                  class="tc-head"
                >
                  {{ c.attacker_attr }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="tc-def-cell">
                  <div
                    v-for="d in pokemon.defensive_type_chart.defender_attrs"
                    :key="d"
                    class="tc-def-name"
                  >
                    {{ d }}
                  </div>
                </td>
                <td
                  v-for="c in pokemon.defensive_type_chart.cells"
                  :key="'m-' + c.attacker_attr"
                  class="tc-mult"
                  :class="'tc-' + c.bucket"
                >
                  {{ c.label }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="type-chart-mobile type-chart--mobile" aria-label="受击倍率（手机布局）">
          <div class="type-chart-mobile-def">
            <span class="type-chart-mobile-def-label">本方属性</span>
            <span class="type-chart-mobile-def-val">{{
              pokemon.defensive_type_chart.defender_attrs.join(' + ')
            }}</span>
          </div>
          <div class="type-chart-mobile-grid">
            <div
              v-for="c in pokemon.defensive_type_chart.cells"
              :key="'mob-' + c.attacker_attr"
              class="type-chart-mobile-cell"
            >
              <div class="type-chart-mobile-attr">{{ c.attacker_attr }}</div>
              <div class="type-chart-mobile-mult" :class="'tc-' + c.bucket">{{ c.label }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- ⑤ 属性克制关系（详情库内文案） -->
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

      <!-- ⑥ 技能列表 -->
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
                role="button"
                :aria-label="`${sk.name}，描述：${(sk.desc && String(sk.desc).trim()) || '暂无描述'}`"
                @click="focusSkillCell"
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
      </div>

      <aside class="detail-side">
        <section class="card evolution-card">
          <h2 class="section-title">进化链</h2>
          <div v-if="!evolutionChain?.stages?.length" class="no-data">暂无进化链数据</div>
          <div v-else class="evolution-stages">
            <template v-for="(stage, index) in evolutionChain.stages" :key="stage.sort_order">
              <div class="evolution-stage">
                <div class="evolution-items">
                  <button
                    v-for="item in stage.items"
                    :key="item.name"
                    type="button"
                    class="evolution-item"
                    :class="{ 'is-active': isCurrentEvolutionItem(item.name) }"
                    @click="goToEvolution(item.name)"
                  >
                    <div class="evolution-item-image-wrap">
                      <img
                        v-if="item.image_url"
                        :src="item.image_url"
                        :alt="item.name"
                        class="evolution-item-image"
                      />
                      <div v-else class="evolution-item-placeholder">?</div>
                    </div>
                    <div class="evolution-item-name">{{ item.name }}</div>
                  </button>
                </div>
              </div>

              <div v-if="index < evolutionChain.stages.length - 1" class="evolution-arrow-block">
                <div class="evolution-arrow">↓</div>
                <div v-if="stage.next_condition" class="evolution-condition">
                  {{ stage.next_condition }}
                </div>
              </div>
            </template>
          </div>
        </section>
      </aside>
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
  max-width: 1240px;
  margin: 0 auto;
  padding: 24px 20px 60px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 20px;
}

.detail-content {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-side {
  min-width: 0;
}

.evolution-card {}

.evolution-stages {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* flex wrap：每行固定3个，最后一行不足时自动居中 */
.evolution-items {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.evolution-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  /* 固定占 1/3 宽度（减去 gap）*/
  flex: 0 0 calc(33.33% - 6px);
  max-width: calc(33.33% - 6px);
  padding: 8px 6px 10px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-bg);
  color: var(--color-text);
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

.evolution-item:hover {
  border-color: var(--color-accent);
  transform: translateY(-1px);
}

.evolution-item.is-active {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.14);
}

.evolution-item-image-wrap {
  width: 52px;
  height: 52px;
  border-radius: 10px;
  background: var(--color-img-bg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.evolution-item-image {
  max-width: 44px;
  max-height: 44px;
  object-fit: contain;
}

.evolution-item-placeholder {
  font-size: 30px;
  color: var(--color-muted);
}

.evolution-item-name {
  width: 100%;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.4;
  text-align: center;
  word-break: break-word;
}

.evolution-arrow-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.evolution-arrow {
  font-size: 26px;
  line-height: 1;
  color: var(--color-muted);
}

.evolution-condition {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--color-hover);
  color: var(--color-muted);
  font-size: 12px;
  line-height: 1.4;
  text-align: center;
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

/* 受击倍率表 */
.type-chart-hint {
  font-size: 13px;
  color: var(--color-muted);
  line-height: 1.5;
  margin: -6px 0 14px;
}

.type-chart-def {
  color: var(--color-text);
  font-weight: 600;
}

.type-chart-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  border: 1px solid var(--color-border);
  border-radius: 12px;
}

.type-chart-table {
  width: max-content;
  min-width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.type-chart-table th,
.type-chart-table td {
  border: 1px solid var(--color-border);
  padding: 8px 10px;
  text-align: center;
  white-space: nowrap;
  background: var(--color-surface);
}

.type-chart-table thead th {
  font-weight: 700;
  color: var(--color-text);
  background: var(--color-hover);
}

.tc-corner {
  min-width: 96px;
  position: sticky;
  left: 0;
  z-index: 2;
  box-shadow: 1px 0 0 var(--color-border);
}

.tc-def-cell {
  min-width: 88px;
  position: sticky;
  left: 0;
  z-index: 1;
  font-weight: 600;
  text-align: left;
  vertical-align: middle;
  box-shadow: 1px 0 0 var(--color-border);
}

.tc-def-name + .tc-def-name {
  margin-top: 4px;
}

.tc-mult {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.tc-super {
  color: #ef4444;
}

.tc-neutral {
  color: #22c55e;
}

.tc-resist {
  color: #3b82f6;
}

.tc-immune {
  color: var(--color-text);
}

.type-chart--mobile {
  display: none;
}

.type-chart-mobile {
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 12px 10px 14px;
  background: var(--color-surface);
}

.type-chart-mobile-def {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px 10px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--color-border);
  font-size: 12px;
}

.type-chart-mobile-def-label {
  color: var(--color-muted);
  font-weight: 600;
}

.type-chart-mobile-def-val {
  color: var(--color-text);
  font-weight: 700;
}

.type-chart-mobile-grid {
  display: grid;
  /* 18 个属性：默认两排各 9 列 */
  grid-template-columns: repeat(9, minmax(0, 1fr));
  gap: 6px 4px;
}

.type-chart-mobile-cell {
  min-width: 0;
  text-align: center;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 6px 2px 7px;
  background: var(--color-bg);
}

.type-chart-mobile-attr {
  font-size: 11px;
  font-weight: 700;
  color: var(--color-text);
  line-height: 1.25;
  word-break: keep-all;
  overflow-wrap: anywhere;
}

.type-chart-mobile-mult {
  margin-top: 4px;
  font-size: 13px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}

@media (max-width: 360px) {
  .type-chart-mobile-grid {
    /* 极窄屏三排各 6 列，仍不横向滚动 */
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }

  .type-chart-mobile-attr {
    font-size: 10px;
  }

  .type-chart-mobile-mult {
    font-size: 12px;
  }
}

@media (max-width: 720px) {
  .type-chart--desktop {
    display: none !important;
  }

  .type-chart--mobile {
    display: block;
  }
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

.egg-groups {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
}

.egg-label {
  font-size: 12px;
  color: var(--color-muted);
  margin-right: 2px;
}

.badge-egg {
  background: rgba(251, 191, 36, 0.18);
  color: #d97706;
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
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
}

/* 点击/聚焦技能名显示说明（原样式写在 max-width:600px 内，宽屏网页没有任何浮层规则） */
.skills-card {
  overflow: visible;
}

.skill-table,
.skill-table tbody,
.skill-table tr,
.skill-table td {
  overflow: visible;
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
}

@media (max-width: 1024px) {
  .detail-main {
    max-width: 860px;
    grid-template-columns: 1fr;
  }
}
</style>
