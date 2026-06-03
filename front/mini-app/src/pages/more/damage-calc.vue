<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DamagePokemonColumn from '@/components/DamagePokemonColumn.vue'
import BottomSheet from '@/components/BottomSheet.vue'
import { calcDamage } from '@/api/damage'
import { fetchPersonalities } from '@/api/pokemon'
import type { PersonalityOption, PokemonDetail, Skill } from '@/types/pokemon'
import type {
  DamageCalcRequest,
  DamageCalcResponse,
  DamageStatResponse,
  SkillCategory,
} from '@/types/damage'

type SideData = { detail: PokemonDetail; stats: DamageStatResponse }

// ── 共享 ──
const level = ref(60)
const attacker = ref<SideData | null>(null)
const defender = ref<SideData | null>(null)
const personalities = ref<PersonalityOption[]>([])

onLoad(() => {
  void loadPersonalities()
})

async function loadPersonalities() {
  try {
    personalities.value = (await fetchPersonalities()) ?? []
  } catch {
    personalities.value = []
  }
}

// ── 技能威力配置 ──
const knownPower = ref(false) // 是否已知技能威力：false=否(基础威力) true=是(已知)
const skillCategory = ref<SkillCategory>('物攻')

// known 模式
const knownPowerInput = ref('')

// base 模式
const skillPickerOpen = ref(false)
const skillKeyword = ref('')
const selectedSkill = ref<Skill | null>(null)
const baseSkillAttr = ref('')
const basePowerInput = ref('')
const powerDeltaInput = ref('') // 威力固定加值，普通数值
// 以下均为百分比展示，传后端转小数
const traitAtkInput = ref('')
const traitPowerInput = ref('')
const otherAtkInput = ref('')
const otherPowerInput = ref('')
const defenderDefInput = ref('')

const comboInput = ref('1')
const reductionInput = ref('') // 防御方应对技能减伤（百分比）

const result = ref<DamageCalcResponse | null>(null)
const calcError = ref('')
const calculating = ref(false)

const attackerSkills = computed<Skill[]>(() => attacker.value?.detail.skills ?? [])

const filteredSkills = computed<Skill[]>(() => {
  const kw = skillKeyword.value.trim().toLowerCase()
  if (!kw) return attackerSkills.value
  return attackerSkills.value.filter(
    (s) =>
      s.name.toLowerCase().includes(kw) ||
      (s.attr ?? '').toLowerCase().includes(kw) ||
      (s.desc ?? '').toLowerCase().includes(kw),
  )
})

function toNum(v: string, fallback = 0): number {
  const n = Number((v ?? '').toString().trim())
  return Number.isFinite(n) ? n : fallback
}

function pct(v: string): number {
  return toNum(v, 0) / 100
}

const comboCount = computed(() => {
  const n = Math.floor(toNum(comboInput.value, 1))
  return n >= 1 ? n : 1
})

const reductionPct = computed(() => pct(reductionInput.value))

const reducedDamage = computed(() => {
  if (!result.value) return null
  if (!reductionInput.value.trim() || reductionPct.value === 0) return null
  return Math.round(result.value.damage * (1 - reductionPct.value))
})

function onAttackerChange(v: SideData | null) {
  attacker.value = v
  // 进攻方更换后，已选技能可能失效，重置技能选择
  selectedSkill.value = null
  baseSkillAttr.value = ''
  basePowerInput.value = ''
}

function onDefenderChange(v: SideData | null) {
  defender.value = v
}

function setKnownPower(val: boolean) {
  knownPower.value = val
}

function setCategory(cat: SkillCategory) {
  skillCategory.value = cat
  // 手动改类别 → 视为脱离已选技能（二选一）
  selectedSkill.value = null
  baseSkillAttr.value = ''
}

function selectSkill(skill: Skill) {
  selectedSkill.value = skill
  basePowerInput.value = String(skill.power ?? 0)
  baseSkillAttr.value = skill.attr || ''
  if (skill.type === '物攻' || skill.type === '魔攻') {
    skillCategory.value = skill.type
  }
  skillPickerOpen.value = false
}

function openSkillPicker() {
  skillKeyword.value = ''
  skillPickerOpen.value = true
}

function onBasePowerInput() {
  // 手动改威力 → 脱离已选技能
  selectedSkill.value = null
  baseSkillAttr.value = ''
}

const canCalc = computed(() => {
  if (!attacker.value || !defender.value) return false
  if (knownPower.value) return toNum(knownPowerInput.value) > 0
  return toNum(basePowerInput.value) > 0
})

function buildRequest(): DamageCalcRequest {
  const a = attacker.value!.stats
  const d = defender.value!.stats
  const req: DamageCalcRequest = {
    attacker: { atk: a.atk.value, matk: a.matk.value },
    defender: { def_val: d.def_val.value, mdef: d.mdef.value },
    combo_count: comboCount.value,
    power_mode: knownPower.value ? 'known' : 'base',
    skill_category: skillCategory.value,
  }
  if (knownPower.value) {
    req.power = toNum(knownPowerInput.value)
  } else {
    req.skill_base_power = toNum(basePowerInput.value)
    req.skill_attr = baseSkillAttr.value || null
    req.attacker_attrs = (attacker.value!.detail.attributes ?? []).map((x) => x.attr_name)
    req.defender_attrs = (defender.value!.detail.attributes ?? []).map((x) => x.attr_name)
    req.power_delta = toNum(powerDeltaInput.value)
    req.trait_atk_bonus = pct(traitAtkInput.value)
    req.trait_power_bonus = pct(traitPowerInput.value)
    req.other_atk_bonus = pct(otherAtkInput.value)
    req.other_power_bonus = pct(otherPowerInput.value)
    req.defender_def_bonus = pct(defenderDefInput.value)
  }
  return req
}

let calcTimer: ReturnType<typeof setTimeout> | null = null

async function runCalc() {
  if (!canCalc.value) {
    result.value = null
    calcError.value = ''
    return
  }
  calculating.value = true
  calcError.value = ''
  try {
    result.value = await calcDamage(buildRequest())
  } catch (e) {
    result.value = null
    calcError.value = (e as Error)?.message || '计算失败'
  } finally {
    calculating.value = false
  }
}

// 任一输入变化 → 自动计算（无需确认）
watch(
  () => [
    attacker.value,
    defender.value,
    knownPower.value,
    skillCategory.value,
    knownPowerInput.value,
    basePowerInput.value,
    baseSkillAttr.value,
    powerDeltaInput.value,
    traitAtkInput.value,
    traitPowerInput.value,
    otherAtkInput.value,
    otherPowerInput.value,
    defenderDefInput.value,
    comboInput.value,
  ],
  () => {
    if (calcTimer) clearTimeout(calcTimer)
    calcTimer = setTimeout(() => void runCalc(), 250)
  },
  { deep: true },
)
</script>

<template>
  <view class="page">
    <view class="title-card">
      <text class="page-title">伤害计算</text>
      <text class="page-subtitle">选择进攻 / 防御方宠物，配置技能即可实时估算 PVP 伤害。</text>
      <view class="level-row">
        <text class="level-label">等级</text>
        <input v-model.number="level" class="level-input" type="number" placeholder="60" />
      </view>
    </view>

    <!-- 两列：进攻方 / 防御方 -->
    <view class="columns">
      <DamagePokemonColumn
        title="进攻方"
        accent="#f56c6c"
        :level="level"
        :personalities="personalities"
        @change="onAttackerChange"
      />
      <DamagePokemonColumn
        title="防御方"
        accent="#2b74ff"
        :level="level"
        :personalities="personalities"
        @change="onDefenderChange"
      />
    </view>

    <!-- 技能威力配置 -->
    <view class="config-card">
      <text class="card-title">技能配置</text>

      <!-- 是否已知威力 -->
      <view class="field">
        <text class="field-label">是否已知技能威力</text>
        <view class="seg">
          <text class="seg-item" :class="{ active: knownPower }" @tap="setKnownPower(true)">是</text>
          <text class="seg-item" :class="{ active: !knownPower }" @tap="setKnownPower(false)">否</text>
        </view>
      </view>

      <!-- 技能类别（两种模式都需要，用于选择攻/防） -->
      <view class="field">
        <text class="field-label">技能类型</text>
        <view class="seg">
          <text
            class="seg-item"
            :class="{ active: skillCategory === '物攻' }"
            @tap="setCategory('物攻')"
          >物攻</text>
          <text
            class="seg-item"
            :class="{ active: skillCategory === '魔攻' }"
            @tap="setCategory('魔攻')"
          >魔攻</text>
        </view>
      </view>

      <!-- 已知威力 -->
      <view v-if="knownPower" class="field">
        <text class="field-label">技能威力</text>
        <input v-model="knownPowerInput" class="num-input" type="number" placeholder="输入威力" />
      </view>

      <!-- 基础威力模式 -->
      <template v-else>
        <!-- 技能选择入口 -->
        <view class="field-col">
          <text class="field-label">技能（点击搜索选择，自动填充威力与类型）</text>
          <view class="skill-select" @tap="openSkillPicker">
            <template v-if="selectedSkill">
              <image
                v-if="selectedSkill.icon"
                class="skill-sel-icon"
                :src="selectedSkill.icon"
                mode="aspectFit"
              />
              <view class="skill-sel-meta">
                <text class="skill-sel-name">{{ selectedSkill.name }}</text>
                <text class="skill-sel-sub">
                  威力 {{ selectedSkill.power }} · {{ selectedSkill.type || '—' }}
                  <text v-if="selectedSkill.attr"> · {{ selectedSkill.attr }}</text>
                </text>
              </view>
            </template>
            <text v-else class="skill-sel-placeholder">
              {{ attacker ? '点击选择技能' : '请先选择进攻方宠物' }}
            </text>
            <text class="picker-field-icon">▾</text>
          </view>
        </view>

        <view class="field">
          <text class="field-label">技能威力</text>
          <input
            v-model="basePowerInput"
            class="num-input"
            type="number"
            placeholder="输入或选择技能"
            @input="onBasePowerInput"
          />
        </view>

        <view class="grid2">
          <view class="field-col">
            <text class="field-label">威力固定加值</text>
            <input v-model="powerDeltaInput" class="num-input" type="text" placeholder="0" />
          </view>
          <view class="field-col">
            <text class="field-label">特性攻击力加成(%)</text>
            <input v-model="traitAtkInput" class="num-input" type="text" placeholder="0" />
          </view>
          <view class="field-col">
            <text class="field-label">特性威力加成(%)</text>
            <input v-model="traitPowerInput" class="num-input" type="text" placeholder="0" />
          </view>
          <view class="field-col">
            <text class="field-label">其他攻击力加成(%)</text>
            <input v-model="otherAtkInput" class="num-input" type="text" placeholder="0" />
          </view>
          <view class="field-col">
            <text class="field-label">其他威力加成(%)</text>
            <input v-model="otherPowerInput" class="num-input" type="text" placeholder="0" />
          </view>
          <view class="field-col">
            <text class="field-label">被进攻方防御加成(%)</text>
            <input v-model="defenderDefInput" class="num-input" type="text" placeholder="0" />
          </view>
        </view>
      </template>

      <view class="grid2">
        <view class="field-col">
          <text class="field-label">连击次数</text>
          <input v-model="comboInput" class="num-input" type="number" placeholder="1" />
        </view>
        <view class="field-col">
          <text class="field-label">防御方技能减伤(%)</text>
          <input v-model="reductionInput" class="num-input" type="text" placeholder="0" />
        </view>
      </view>
    </view>

    <!-- 结果 -->
    <view class="result-card">
      <text class="card-title">伤害结果</text>

      <view v-if="calcError" class="result-err">{{ calcError }}</view>

      <view v-else-if="!canCalc" class="result-hint">
        <text>请选择进攻方、防御方，并填写技能威力</text>
      </view>

      <template v-else-if="result">
        <!-- 含减伤：原伤害 + 减伤后 -->
        <view v-if="reducedDamage !== null" class="dmg-compare">
          <view class="dmg-block muted">
            <text class="dmg-cap">原伤害</text>
            <text class="dmg-num strike">{{ result.damage }}</text>
          </view>
          <text class="dmg-arrow">→</text>
          <view class="dmg-block">
            <text class="dmg-cap">减伤后（-{{ reductionInput }}%）</text>
            <text class="dmg-num main">{{ reducedDamage }}</text>
          </view>
        </view>
        <!-- 无减伤 -->
        <view v-else class="dmg-single">
          <text class="dmg-cap">最终伤害</text>
          <text class="dmg-num main">{{ result.damage }}</text>
        </view>

        <!-- 指标明细 -->
        <view class="metric-row">
          <view class="metric">
            <text class="metric-label">单次伤害</text>
            <text class="metric-value">{{ result.per_hit_damage }}</text>
          </view>
          <view class="metric">
            <text class="metric-label">连击</text>
            <text class="metric-value">×{{ result.combo_count }}</text>
          </view>
          <view class="metric">
            <text class="metric-label">{{ skillCategory === '魔攻' ? '魔攻' : '物攻' }}</text>
            <text class="metric-value">{{ result.attack }}</text>
          </view>
          <view class="metric">
            <text class="metric-label">{{ skillCategory === '魔攻' ? '魔防' : '物防' }}</text>
            <text class="metric-value">{{ result.defense }}</text>
          </view>
        </view>

        <!-- 基础威力模式额外指标 -->
        <view v-if="!knownPower" class="metric-row">
          <view class="metric">
            <text class="metric-label">计算威力</text>
            <text class="metric-value">{{ result.power }}</text>
          </view>
          <view class="metric">
            <text class="metric-label">克制系数</text>
            <text class="metric-value">×{{ result.type_coef }}</text>
          </view>
          <view class="metric">
            <text class="metric-label">本系加成</text>
            <text class="metric-value">{{ result.stab ? '是 ×1.25' : '否' }}</text>
          </view>
        </view>
      </template>
    </view>

    <!-- 技能选择弹层 -->
    <BottomSheet :visible="skillPickerOpen" title="选择技能" @close="skillPickerOpen = false">
      <input
        v-model="skillKeyword"
        class="sheet-search"
        confirm-type="search"
        placeholder="搜索技能名 / 属性"
      />
      <view class="sheet-list-area">
        <view v-if="filteredSkills.length === 0" class="sheet-tip">
          {{ attackerSkills.length ? '无匹配技能' : '该宠物暂无技能数据，可直接手动输入威力' }}
        </view>
        <scroll-view v-else scroll-y class="sheet-scroll">
          <view
            v-for="(sk, i) in filteredSkills"
            :key="i"
            class="skill-item"
            :class="{ active: selectedSkill && selectedSkill.name === sk.name }"
            @tap="selectSkill(sk)"
          >
            <image v-if="sk.icon" class="skill-item-icon" :src="sk.icon" mode="aspectFit" />
            <view class="skill-item-body">
              <view class="skill-item-top">
                <text class="skill-item-name">{{ sk.name }}</text>
                <view class="skill-item-tags">
                  <text v-if="sk.attr" class="skill-tag attr">{{ sk.attr }}</text>
                  <text v-if="sk.type" class="skill-tag type">{{ sk.type }}</text>
                  <text class="skill-tag power">威力 {{ sk.power }}</text>
                </view>
              </view>
              <text v-if="sk.desc" class="skill-item-desc">{{ sk.desc }}</text>
            </view>
          </view>
        </scroll-view>
      </view>
    </BottomSheet>
  </view>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 24rpx;
  background: linear-gradient(180deg, #f3f8ff 0%, #f9fbff 100%);
}

.title-card,
.config-card,
.result-card {
  margin-bottom: 24rpx;
  padding: 28rpx;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 12rpx 32rpx rgba(64, 125, 255, 0.08);
}

.page-title {
  display: block;
  font-size: 36rpx;
  font-weight: 700;
  color: #1f4ea3;
}

.page-subtitle {
  display: block;
  margin-top: 10rpx;
  font-size: 24rpx;
  line-height: 1.6;
  color: #5f7da6;
}

.level-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-top: 20rpx;
}

.level-label {
  font-size: 26rpx;
  color: #1f3760;
  font-weight: 600;
}

.level-input {
  width: 140rpx;
  height: 64rpx;
  padding: 0 20rpx;
  border-radius: 14rpx;
  background: #f3f8ff;
  font-size: 26rpx;
  color: #1e3557;
  text-align: center;
}

.columns {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
  margin-bottom: 24rpx;
}

.card-title {
  display: block;
  font-size: 30rpx;
  font-weight: 700;
  color: #214887;
  margin-bottom: 20rpx;
}

.field {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 20rpx;
}

.field-col {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
  margin-bottom: 20rpx;
}

.field-label {
  font-size: 24rpx;
  color: #5f7da6;
}

.seg {
  display: flex;
  padding: 4rpx;
  border-radius: 14rpx;
  background: #eef4ff;
}

.seg-item {
  padding: 12rpx 30rpx;
  border-radius: 11rpx;
  font-size: 26rpx;
  color: #5f7da6;
}

.seg-item.active {
  background: #2b74ff;
  color: #ffffff;
  font-weight: 600;
}

.num-input {
  height: 64rpx;
  padding: 0 20rpx;
  border-radius: 14rpx;
  background: #f3f8ff;
  font-size: 26rpx;
  color: #1e3557;
}

.field .num-input {
  width: 280rpx;
  text-align: right;
}

.picker-field-icon {
  font-size: 22rpx;
  color: #8aa2c9;
  flex-shrink: 0;
}

.skill-select {
  display: flex;
  align-items: center;
  gap: 14rpx;
  min-height: 72rpx;
  padding: 14rpx 18rpx;
  border-radius: 16rpx;
  background: #f3f8ff;
}

.skill-sel-icon {
  width: 56rpx;
  height: 56rpx;
  flex-shrink: 0;
}

.skill-sel-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.skill-sel-name {
  font-size: 26rpx;
  font-weight: 600;
  color: #1e3557;
}

.skill-sel-sub {
  font-size: 22rpx;
  color: #6f89b2;
}

.skill-sel-placeholder {
  flex: 1;
  font-size: 26rpx;
  color: #9bb1d6;
}

/* ── 技能选择弹层 ── */
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

.skill-item {
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
  padding: 20rpx;
  border-radius: 16rpx;
  margin-bottom: 12rpx;
  background: #f5f9ff;
}

.skill-item.active {
  background: rgba(43, 116, 255, 0.12);
  border: 1px solid #2b74ff;
}

.skill-item-icon {
  width: 64rpx;
  height: 64rpx;
  flex-shrink: 0;
}

.skill-item-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.skill-item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
}

.skill-item-name {
  font-size: 26rpx;
  font-weight: 700;
  color: #1f3760;
}

.skill-item-tags {
  display: flex;
  gap: 6rpx;
  flex-shrink: 0;
}

.skill-tag {
  padding: 3rpx 10rpx;
  border-radius: 999rpx;
  font-size: 18rpx;
}

.skill-tag.attr {
  color: #2761d8;
  background: rgba(39, 97, 216, 0.12);
}

.skill-tag.type {
  color: #169b7b;
  background: rgba(22, 155, 123, 0.12);
}

.skill-tag.power {
  color: #e0773a;
  background: rgba(224, 119, 58, 0.12);
}

.skill-item-desc {
  font-size: 22rpx;
  line-height: 1.6;
  color: #6f89b2;
}

.grid2 {
  display: flex;
  flex-wrap: wrap;
  gap: 0 20rpx;
}

.grid2 .field-col {
  flex: 1 1 calc(50% - 10rpx);
  min-width: calc(50% - 10rpx);
}

.result-hint,
.result-err {
  padding: 30rpx 0;
  font-size: 24rpx;
  text-align: center;
}

.result-hint { color: #9bb1d6; }
.result-err { color: #c74646; }

.dmg-single {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
  padding: 16rpx 0 24rpx;
}

.dmg-compare {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20rpx;
  padding: 16rpx 0 24rpx;
}

.dmg-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}

.dmg-block.muted { opacity: 0.85; }

.dmg-arrow {
  font-size: 40rpx;
  color: #b5c8e8;
}

.dmg-cap {
  font-size: 22rpx;
  color: #7a93bb;
}

.dmg-num {
  font-size: 56rpx;
  font-weight: 800;
  line-height: 1.1;
}

.dmg-num.main {
  color: #f5564a;
}

.dmg-num.strike {
  font-size: 44rpx;
  color: #9bb1d6;
  text-decoration: line-through;
}

.metric-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 16rpx;
}

.metric {
  flex: 1 1 calc(25% - 12rpx);
  min-width: calc(25% - 12rpx);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6rpx;
  padding: 14rpx 6rpx;
  border-radius: 14rpx;
  background: #f5f9ff;
}

.metric-label {
  font-size: 20rpx;
  color: #7a93bb;
}

.metric-value {
  font-size: 26rpx;
  font-weight: 700;
  color: #1f3760;
}
</style>
