<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { fetchPokemon, fetchPokemonDetail } from '@/api/pokemon'
import { calcPokemonStats } from '@/api/damage'
import BottomSheet from '@/components/BottomSheet.vue'
import type { Pokemon, PokemonDetail } from '@/types/pokemon'
import type { PersonalityOption } from '@/types/pokemon'
import type { DamageStatItem, DamageStatResponse } from '@/types/damage'

const props = withDefaults(
  defineProps<{
    title: string
    accent?: string
    level: number
    personalities: PersonalityOption[]
  }>(),
  { accent: '#2b74ff' },
)

const emit = defineEmits<{
  change: [value: { detail: PokemonDetail; stats: DamageStatResponse } | null]
}>()

// 性格修正字段 → 中文标签
const PERSONALITY_STAT_LABEL: Record<string, string> = {
  hp: '生命',
  phy_atk: '物攻',
  mag_atk: '魔攻',
  phy_def: '物防',
  mag_def: '魔防',
  spd: '速度',
}

// 性格分组展示顺序（按加成属性 buff_stat）
const PERSONALITY_GROUP_ORDER = ['phy_atk', 'mag_atk', 'spd', 'phy_def', 'mag_def', 'hp']

// ── 宠物选择 ──
const pickerOpen = ref(false)
const keyword = ref('')
const searching = ref(false)
const results = ref<Pokemon[]>([])

// ── 性格选择 ──
const personaOpen = ref(false)
const selectedPersonalityId = ref<number | null>(null)

// ── 天赋值（个体值）：勾选的属性额外 +60，最多 3 项 ──
const IV_MAX = 3
const ivStats = ref<string[]>([])

const detail = ref<PokemonDetail | null>(null)
const stats = ref<DamageStatResponse | null>(null)
const loadingDetail = ref(false)
const error = ref('')

let searchTimer: ReturnType<typeof setTimeout> | null = null
// 交换攻防时临时抑制重新计算（属性已随状态一并搬运，无需再请求一次）
let suppressRecalc = false

const statList = computed<DamageStatItem[]>(() => {
  if (!stats.value) return []
  const s = stats.value
  return [s.hp, s.atk, s.matk, s.def_val, s.mdef, s.spd]
})

const selectedPersonality = computed<PersonalityOption | null>(() => {
  if (selectedPersonalityId.value == null) return null
  return props.personalities.find((p) => p.id === selectedPersonalityId.value) ?? null
})

// 按加成属性（buff_stat）将性格分组，方便快速选择
const personalityGroups = computed<{ key: string; label: string; items: PersonalityOption[] }[]>(
  () => {
    const map = new Map<string, PersonalityOption[]>()
    const neutral: PersonalityOption[] = []
    for (const p of props.personalities) {
      if (p.is_neutral || !p.buff_stat) {
        neutral.push(p)
        continue
      }
      const arr = map.get(p.buff_stat) ?? []
      arr.push(p)
      map.set(p.buff_stat, arr)
    }
    const groups: { key: string; label: string; items: PersonalityOption[] }[] = []
    const seen = new Set<string>()
    const pushGroup = (key: string, items: PersonalityOption[]) => {
      groups.push({ key, label: `${PERSONALITY_STAT_LABEL[key] ?? key}↑`, items })
      seen.add(key)
    }
    for (const key of PERSONALITY_GROUP_ORDER) {
      const items = map.get(key)
      if (items?.length) pushGroup(key, items)
    }
    // 兜底：顺序表外的其他加成属性
    for (const [key, items] of map) {
      if (!seen.has(key) && items.length) pushGroup(key, items)
    }
    if (neutral.length) groups.push({ key: 'neutral', label: '无加成', items: neutral })
    return groups
  },
)

function personalityEffect(p: PersonalityOption): string {
  if (p.is_neutral || (!p.buff_stat && !p.nerf_stat)) return '无加成'
  const parts: string[] = []
  if (p.buff_stat) parts.push(`${PERSONALITY_STAT_LABEL[p.buff_stat] ?? p.buff_stat}↑`)
  if (p.nerf_stat) parts.push(`${PERSONALITY_STAT_LABEL[p.nerf_stat] ?? p.nerf_stat}↓`)
  return parts.join(' ')
}

// 性格列表就绪后，默认选中中性性格
watch(
  () => props.personalities,
  (list) => {
    if (selectedPersonalityId.value == null && list.length) {
      const neutral = list.find((p) => p.is_neutral)
      selectedPersonalityId.value = (neutral ?? list[0]).id
    }
  },
  { immediate: true },
)

watch(keyword, (val) => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void runSearch(val.trim()), 300)
})

// 等级 / 性格 / 天赋值变化时，已选宠物重新计算属性
watch(
  () => [props.level, selectedPersonalityId.value, ivStats.value],
  () => {
    if (suppressRecalc) return
    if (detail.value) void loadStats(detail.value)
  },
)

function toggleIv(key: string) {
  const idx = ivStats.value.indexOf(key)
  if (idx >= 0) {
    ivStats.value = ivStats.value.filter((k) => k !== key)
    return
  }
  if (ivStats.value.length >= IV_MAX) {
    uni.showToast({ title: `最多选择 ${IV_MAX} 项天赋值`, icon: 'none' })
    return
  }
  ivStats.value = [...ivStats.value, key]
}

async function runSearch(kw: string) {
  searching.value = true
  try {
    const res = await fetchPokemon({ name: kw || undefined, page: 1, page_size: 60 })
    results.value = res?.items ?? []
  } catch {
    results.value = []
  } finally {
    searching.value = false
  }
}

async function openPokemonPicker() {
  pickerOpen.value = true
  if (results.value.length === 0) await runSearch('')
}

async function loadStats(d: PokemonDetail) {
  const lv = Math.min(100, Math.max(1, Math.floor(Number(props.level) || 60)))
  const res = await calcPokemonStats({
    hp: d.stats.hp,
    atk: d.stats.atk,
    matk: d.stats.matk,
    def_val: d.stats.def_val,
    mdef: d.stats.mdef,
    spd: d.stats.spd,
    level: lv,
    personality_id: selectedPersonalityId.value,
    iv_stats: ivStats.value,
  })
  stats.value = res
  emit('change', { detail: d, stats: res })
}

async function selectPokemon(name: string) {
  pickerOpen.value = false
  loadingDetail.value = true
  error.value = ''
  try {
    const d = await fetchPokemonDetail(name)
    detail.value = d
    await loadStats(d)
  } catch {
    error.value = '加载宠物数据失败，请重试'
    detail.value = null
    stats.value = null
    emit('change', null)
  } finally {
    loadingDetail.value = false
  }
}

function selectPersonality(p: PersonalityOption) {
  selectedPersonalityId.value = p.id
  personaOpen.value = false
}

// ── 对外暴露：用于一键交换攻击/防御方，整组配置随状态搬运 ──
type ColumnState = {
  detail: PokemonDetail | null
  stats: DamageStatResponse | null
  personalityId: number | null
  ivStats: string[]
  error: string
}

function getState(): ColumnState {
  return {
    detail: detail.value,
    stats: stats.value,
    personalityId: selectedPersonalityId.value,
    ivStats: [...ivStats.value],
    error: error.value,
  }
}

function applyState(s: ColumnState) {
  suppressRecalc = true
  detail.value = s.detail
  stats.value = s.stats
  selectedPersonalityId.value = s.personalityId
  ivStats.value = [...s.ivStats]
  error.value = s.error
  emit('change', s.detail && s.stats ? { detail: s.detail, stats: s.stats } : null)
  // 等本轮响应式更新刷新后再恢复自动计算，避免误触发一次请求
  void nextTick(() => {
    suppressRecalc = false
  })
}

defineExpose({ getState, applyState })
</script>

<template>
  <view class="column">
    <view class="column-head">
      <view class="dot" :style="{ background: accent }" />
      <text class="column-title">{{ title }}</text>
    </view>

    <!-- 选择宠物入口 -->
    <view class="picker-field" @tap="openPokemonPicker">
      <text v-if="detail" class="picker-field-text">{{ detail.name }}</text>
      <text v-else class="picker-field-placeholder">点击搜索 / 选择宠物</text>
      <text class="picker-field-icon">▾</text>
    </view>

    <view v-if="error" class="err">{{ error }}</view>

    <!-- 加载占位 -->
    <view v-if="loadingDetail" class="skeleton" />

    <!-- 未选择 -->
    <view v-else-if="!detail" class="empty">
      <text class="empty-text">尚未选择宠物</text>
    </view>

    <!-- 已选择 -->
    <view v-else class="selected">
      <view class="pet-head">
        <image v-if="detail.image_url" class="pet-img" :src="detail.image_url" mode="aspectFit" />
        <view class="pet-meta">
          <text class="pet-name">{{ detail.name }}</text>
          <view class="attr-row">
            <view v-for="a in detail.attributes" :key="a.attr_name" class="attr-chip">
              <image v-if="a.attr_image" class="attr-icon" :src="a.attr_image" mode="aspectFit" />
              <text class="attr-text">{{ a.attr_name }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 性格选择 -->
      <view class="persona-field" @tap="personaOpen = true">
        <view class="persona-info">
          <text class="persona-cap">性格</text>
          <text class="persona-name">{{ selectedPersonality?.name ?? '默认' }}</text>
        </view>
        <view class="persona-right">
          <text v-if="selectedPersonality" class="persona-eff">
            {{ personalityEffect(selectedPersonality) }}
          </text>
          <text class="picker-field-icon">▾</text>
        </view>
      </view>

      <!-- 特性 -->
      <view v-if="detail.trait && detail.trait.name" class="trait">
        <text class="trait-name">特性 · {{ detail.trait.name }}</text>
        <text v-if="detail.trait.desc" class="trait-desc">{{ detail.trait.desc }}</text>
      </view>

      <!-- 六维真实属性 + 天赋值（个体值）勾选 -->
      <view v-if="statList.length" class="stat-block">
        <text class="stat-hint">点击属性勾选天赋值（+60，最多 3 项）</text>
        <view class="stat-grid">
          <view
            v-for="st in statList"
            :key="st.key"
            class="stat-cell"
            :class="{ selected: ivStats.includes(st.key) }"
            @tap="toggleIv(st.key)"
          >
            <view class="stat-check" :class="{ on: ivStats.includes(st.key) }">
              <text v-if="ivStats.includes(st.key)" class="check-mark">✓</text>
            </view>
            <text class="stat-label">{{ st.label }}</text>
            <text class="stat-value">{{ st.value }}</text>
            <text class="stat-iv" :class="{ show: ivStats.includes(st.key) }">天赋+60</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 宠物选择弹层 -->
    <BottomSheet :visible="pickerOpen" title="选择宠物" @close="pickerOpen = false">
      <input
        v-model="keyword"
        class="sheet-search"
        confirm-type="search"
        placeholder="输入宠物名搜索"
      />
      <view class="sheet-list-area">
        <view v-if="searching && results.length === 0" class="sheet-tip">搜索中…</view>
        <view v-else-if="results.length === 0" class="sheet-tip">无匹配宠物</view>
        <scroll-view v-else scroll-y class="sheet-scroll">
          <view class="poke-grid">
            <view
              v-for="p in results"
              :key="p.id"
              class="poke-cell"
              @tap="selectPokemon(p.name)"
            >
              <image v-if="p.image_url" class="poke-img" :src="p.image_url" mode="aspectFit" lazy-load />
              <text class="poke-name">{{ p.name }}</text>
              <text v-if="p.form_name" class="poke-form">{{ p.form_name }}</text>
            </view>
          </view>
        </scroll-view>
      </view>
    </BottomSheet>

    <!-- 性格选择弹层 -->
    <BottomSheet :visible="personaOpen" title="选择性格" @close="personaOpen = false">
      <view class="sheet-list-area">
        <scroll-view scroll-y class="sheet-scroll">
          <view v-for="g in personalityGroups" :key="g.key" class="persona-group">
            <text class="persona-group-title">{{ g.label }}</text>
            <view
              v-for="p in g.items"
              :key="p.id"
              class="persona-item"
              :class="{ active: p.id === selectedPersonalityId }"
              @tap="selectPersonality(p)"
            >
              <text class="persona-item-name">{{ p.name }}</text>
              <text class="persona-item-eff" :class="{ neutral: p.is_neutral }">
                {{ personalityEffect(p) }}
              </text>
            </view>
          </view>
        </scroll-view>
      </view>
    </BottomSheet>
  </view>
</template>

<style scoped>
.column {
  /* 纵向排列：每个模块占满整行宽度，内容充分展开 */
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
  padding: 22rpx 18rpx;
  border-radius: 24rpx;
  background: #ffffff;
  box-shadow: 0 10rpx 28rpx rgba(64, 125, 255, 0.08);
}

.column-head {
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.dot {
  width: 14rpx;
  height: 14rpx;
  border-radius: 50%;
}

.column-title {
  font-size: 28rpx;
  font-weight: 700;
  color: #1f3760;
}

.picker-field {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 72rpx;
  padding: 0 20rpx;
  border-radius: 16rpx;
  background: #f3f8ff;
}

.picker-field-text {
  font-size: 26rpx;
  font-weight: 600;
  color: #1e3557;
}

.picker-field-placeholder {
  font-size: 26rpx;
  color: #9bb1d6;
}

.picker-field-icon {
  font-size: 22rpx;
  color: #8aa2c9;
}

.err {
  font-size: 24rpx;
  color: #c74646;
}

.skeleton {
  height: 320rpx;
  border-radius: 18rpx;
  background: linear-gradient(135deg, #edf4ff 0%, #ffffff 100%);
}

.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 180rpx;
  border-radius: 18rpx;
  border: 1px dashed #c7d8f2;
}

.empty-text {
  font-size: 24rpx;
  color: #9bb1d6;
}

.selected {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.pet-head {
  display: flex;
  align-items: flex-start;
  gap: 14rpx;
}

.pet-img {
  width: 96rpx;
  height: 96rpx;
  border-radius: 16rpx;
  background: linear-gradient(180deg, #edf5ff 0%, #f8fbff 100%);
  flex-shrink: 0;
}

.pet-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.pet-name {
  font-size: 28rpx;
  font-weight: 700;
  color: #1e3557;
}

.attr-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6rpx;
}

.attr-chip {
  display: inline-flex;
  align-items: center;
  gap: 4rpx;
  padding: 3rpx 10rpx;
  border-radius: 999rpx;
  background: #eff5ff;
}

.attr-icon {
  width: 20rpx;
  height: 20rpx;
}

.attr-text {
  font-size: 18rpx;
  color: #45638e;
}

.persona-field {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
  padding: 14rpx 18rpx;
  border-radius: 16rpx;
  background: #f7faff;
  border: 1px solid #e6eefb;
}

.persona-info {
  display: flex;
  align-items: center;
  gap: 12rpx;
  min-width: 0;
}

.persona-cap {
  font-size: 22rpx;
  color: #7a93bb;
}

.persona-name {
  font-size: 26rpx;
  font-weight: 700;
  color: #2761d8;
}

.persona-right {
  display: flex;
  align-items: center;
  gap: 10rpx;
  flex-shrink: 0;
}

.persona-eff {
  font-size: 22rpx;
  color: #6f89b2;
}

.trait {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
  padding: 16rpx;
  border-radius: 16rpx;
  background: #f7faff;
}

.trait-name {
  font-size: 24rpx;
  font-weight: 700;
  color: #2761d8;
}

.trait-desc {
  font-size: 22rpx;
  line-height: 1.6;
  color: #6f89b2;
}

.stat-block {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}

.stat-hint {
  font-size: 20rpx;
  color: #9bb1d6;
}

.stat-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}

.stat-cell {
  position: relative;
  flex: 1 1 calc(33.33% - 10rpx);
  min-width: calc(33.33% - 10rpx);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4rpx;
  padding: 16rpx 6rpx 12rpx;
  border-radius: 14rpx;
  background: #f3f8ff;
  border: 1px solid transparent;
}

.stat-cell.selected {
  background: rgba(245, 138, 58, 0.1);
  border-color: #f5a04a;
}

.stat-check {
  position: absolute;
  top: 8rpx;
  right: 8rpx;
  width: 26rpx;
  height: 26rpx;
  border-radius: 50%;
  border: 1px solid #c7d8f2;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-check.on {
  border-color: #f5a04a;
  background: #f5a04a;
}

.check-mark {
  font-size: 18rpx;
  color: #ffffff;
  line-height: 1;
}

.stat-label {
  font-size: 20rpx;
  color: #7a93bb;
}

.stat-value {
  font-size: 30rpx;
  font-weight: 700;
  color: #1f3760;
}

.stat-iv {
  font-size: 16rpx;
  color: transparent;
  line-height: 1.2;
}

.stat-iv.show {
  color: #e0773a;
}

/* ── 弹层内容 ── */
.sheet-search {
  height: 72rpx;
  padding: 0 24rpx;
  margin-bottom: 18rpx;
  border-radius: 16rpx;
  background: #f3f8ff;
  font-size: 26rpx;
  color: #1e3557;
  flex-shrink: 0;
}

/* 列表区固定高度：结果多少都不改变弹层高度，少则下方留空 */
.sheet-list-area {
  height: 56vh;
}

.sheet-tip {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: 24rpx;
  color: #9bb1d6;
}

.sheet-scroll {
  height: 100%;
}

.poke-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}

.poke-cell {
  width: calc(33.33% - 12rpx);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4rpx;
  padding: 16rpx 8rpx;
  border-radius: 16rpx;
  background: #f5f9ff;
}

.poke-img {
  width: 96rpx;
  height: 96rpx;
}

.poke-name {
  font-size: 22rpx;
  color: #1f3760;
  text-align: center;
  line-height: 1.3;
}

.poke-form {
  font-size: 18rpx;
  color: #8aa2c9;
}

.persona-group {
  margin-bottom: 8rpx;
}

.persona-group-title {
  display: block;
  margin: 6rpx 4rpx 12rpx;
  font-size: 22rpx;
  font-weight: 700;
  color: #2761d8;
}

.persona-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 22rpx 20rpx;
  border-radius: 16rpx;
  margin-bottom: 12rpx;
  background: #f5f9ff;
}

.persona-item.active {
  background: rgba(43, 116, 255, 0.12);
  border: 1px solid #2b74ff;
}

.persona-item-name {
  font-size: 26rpx;
  font-weight: 600;
  color: #1f3760;
}

.persona-item-eff {
  font-size: 22rpx;
  color: #e0773a;
}

.persona-item-eff.neutral {
  color: #9bb1d6;
}
</style>
