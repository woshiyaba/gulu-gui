<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import {
  fetchAttributes,
  fetchBattlePkRandomPokemonModes,
  fetchBloodlines,
  fetchLineups,
  fetchPersonalities,
  fetchPokemon,
  fetchPokemonDetail,
  fetchResonanceMagics,
  fetchSkills,
  submitBattlePk,
} from '@/api/pokemon'
import type {
  Attribute,
  BattlePkMember,
  BattlePkRandomPokemonOption,
  BattlePkResponse,
  BattlePkTeam,
  BloodlineOption,
  PersonalityOption,
  Pokemon,
  ResonanceMagicOption,
  Skill,
} from '@/types/pokemon'
import type { Lineup } from '@/types/banner'

type TeamKey = 'A' | 'B'

interface MemberForm {
  pokemon_id: number | null
  pokemon_name: string
  pokemon_image: string
  pokemon_attrs: string[]
  sort_order: number
  bloodline_dict_id: number | null
  bloodline_label: string
  personality_id: number | null
  personality_name_zh: string
  qual_1: string
  qual_2: string
  qual_3: string
  skills: Array<{ name: string; image: string }>
  member_desc: string
  random_pk_dict_id: number | null
}

interface TeamForm {
  title: string
  lineup_desc: string
  resonance_magic_id: number | null
  resonance_magic_name: string
  members: MemberForm[]
}

const STAT_OPTIONS = [
  { value: 'hp', label: 'HP' },
  { value: 'phy_atk', label: '物攻' },
  { value: 'mag_atk', label: '魔攻' },
  { value: 'phy_def', label: '物防' },
  { value: 'mag_def', label: '魔防' },
  { value: 'spd', label: '速度' },
] as const

const STAT_LABEL_MAP: Record<string, string> = {
  hp: 'HP',
  phy_atk: '物攻',
  mag_atk: '魔攻',
  phy_def: '物防',
  mag_def: '魔防',
  spd: '速度',
}

function emptyMember(sort: number): MemberForm {
  return {
    pokemon_id: null,
    pokemon_name: '',
    pokemon_image: '',
    pokemon_attrs: [],
    sort_order: sort,
    bloodline_dict_id: null,
    bloodline_label: '',
    personality_id: null,
    personality_name_zh: '',
    qual_1: '',
    qual_2: '',
    qual_3: '',
    skills: [
      { name: '', image: '' },
      { name: '', image: '' },
      { name: '', image: '' },
      { name: '', image: '' },
    ],
    member_desc: '',
    random_pk_dict_id: null,
  }
}

function emptyTeam(title: string): TeamForm {
  return {
    title,
    lineup_desc: '',
    resonance_magic_id: null,
    resonance_magic_name: '',
    members: [emptyMember(1)],
  }
}

const teamA = reactive<TeamForm>(emptyTeam('我的队伍'))
const teamB = reactive<TeamForm>(emptyTeam('对手队伍'))
const activeTeam = ref<TeamKey>('A')

const personalities = ref<PersonalityOption[]>([])
const bloodlines = ref<BloodlineOption[]>([])
const attributes = ref<Attribute[]>([])
const resonanceMagics = ref<ResonanceMagicOption[]>([])
const lineupOptions = ref<Lineup[]>([])
const lineupLoading = ref(false)
const importLineupId = reactive<Record<TeamKey, number | null>>({
  A: null,
  B: null,
})

const randomPokemonModes = ref<BattlePkRandomPokemonOption[]>([])

const submitting = ref(false)
const error = ref('')
const result = ref<BattlePkResponse | null>(null)

// 弹层统一抽象：用一个 picker state 管理所有底部弹层
type PickerKind =
  | 'pokemon'   // 选精灵
  | 'skill'     // 选技能
  | 'personality' // 选性格
  | 'bloodline' // 选血脉
  | 'resonance' // 选共鸣魔法
  | 'qual'      // 选资质
  | 'none'

interface PickerCtx {
  team: TeamKey
  memberIndex: number
  skillIndex?: number
  qualIndex?: 1 | 2 | 3
}

const pickerKind = ref<PickerKind>('none')
const pickerCtx = ref<PickerCtx | null>(null)
const pickerKeyword = ref('')
const pickerLoading = ref(false)
const pokemonSearchLoading = ref(false)
const pokemonHits = ref<Pokemon[]>([])
const skillHits = ref<Skill[]>([])
const selectedSkill = ref<Skill | null>(null)
// 'pet'：仅展示当前精灵已配置的技能；'search'：调用接口按属性/名字搜索
const skillSource = ref<'pet' | 'search'>('pet')
const skillAttrFilter = ref<string>('')
const petSkills = ref<Skill[]>([])

// 弹层中实际用于渲染的技能列表
const visibleSkills = computed<Skill[]>(() => {
  if (skillSource.value === 'pet') {
    const kw = pickerKeyword.value.trim().toLowerCase()
    if (!kw) return petSkills.value
    return petSkills.value.filter((s) => (s.name || '').toLowerCase().includes(kw))
  }
  return skillHits.value
})

// 技能弹层属性 chips：当前精灵的属性，无精灵时返回空数组
const skillPickerAttrs = computed<string[]>(() => {
  const ctx = pickerCtx.value
  if (!ctx) return []
  const m = teamRef(ctx.team).members[ctx.memberIndex]
  return m?.pokemon_attrs || []
})

let searchTimer: ReturnType<typeof setTimeout> | undefined

function teamRef(key: TeamKey): TeamForm {
  return key === 'A' ? teamA : teamB
}

function applyLineupToTeam(team: TeamKey, lineup: Lineup) {
  const t = teamRef(team)
  t.title = lineup.title || (team === 'A' ? '我的队伍' : '对手队伍')
  t.lineup_desc = lineup.lineup_desc || ''
  t.resonance_magic_id = lineup.resonance_magic_id ?? null
  t.resonance_magic_name = lineup.resonance_magic_name || ''
  t.members = lineup.members.slice(0, 6).map((m, i) => ({
    pokemon_id: m.pokemon_id ?? null,
    pokemon_name: m.pokemon_name || '',
    pokemon_image: m.pokemon_image || '',
    pokemon_attrs: [],
    sort_order: i + 1,
    bloodline_dict_id: m.bloodline_dict_id ?? null,
    bloodline_label: m.bloodline_label || '',
    personality_id: m.personality_id ?? null,
    personality_name_zh: m.personality_name_zh || '',
    qual_1: m.qual_1 || '',
    qual_2: m.qual_2 || '',
    qual_3: m.qual_3 || '',
    skills: [
      { name: m.skill_1_name || '', image: m.skill_1_image || '' },
      { name: m.skill_2_name || '', image: m.skill_2_image || '' },
      { name: m.skill_3_name || '', image: m.skill_3_image || '' },
      { name: m.skill_4_name || '', image: m.skill_4_image || '' },
    ],
    member_desc: m.member_desc || '',
    random_pk_dict_id: null,
  }))
  if (!t.members.length) t.members = [emptyMember(1)]
}

function importPresetLineup(team: TeamKey) {
  const lineupId = importLineupId[team]
  if (!lineupId) {
    const msg = `请先为${team === 'A' ? '我方' : '对手'}选择阵容`
    error.value = msg
    uni.showToast({ title: msg, icon: 'none' })
    return
  }
  const picked = lineupOptions.value.find((item) => item.id === lineupId)
  if (!picked) {
    const msg = '阵容不存在或已失效，请重新选择'
    error.value = msg
    uni.showToast({ title: msg, icon: 'none' })
    return
  }
  applyLineupToTeam(team, picked)
  error.value = ''
  uni.showToast({ title: '已导入阵容', icon: 'none' })
}

const personalityById = computed(() => {
  const map = new Map<number, PersonalityOption>()
  for (const p of personalities.value) map.set(p.id, p)
  return map
})
const resonanceById = computed(() => {
  const map = new Map<number, ResonanceMagicOption>()
  for (const m of resonanceMagics.value) map.set(m.id, m)
  return map
})

function personalityDesc(p: PersonalityOption): string {
  const pairs: Array<[string, number]> = [
    ['hp', p.hp_mod_pct],
    ['phy_atk', p.phy_atk_mod_pct],
    ['mag_atk', p.mag_atk_mod_pct],
    ['phy_def', p.phy_def_mod_pct],
    ['mag_def', p.mag_def_mod_pct],
    ['spd', p.spd_mod_pct],
  ]
  const buffs = pairs.filter(([, v]) => v > 0)
  const nerfs = pairs.filter(([, v]) => v < 0)
  if (!buffs.length && !nerfs.length) return '中性，不影响任何属性'
  // 后端 *_mod_pct 是小数（0.1 = 10%），这里转成百分比展示。
  const fmt = (k: string, v: number) => {
    const pct = Math.round(v * 100)
    return `${STAT_LABEL_MAP[k] || k} ${pct > 0 ? '+' : ''}${pct}%`
  }
  const buffStr = buffs.length ? `加：${buffs.map(([k, v]) => fmt(k, v)).join('、')}` : ''
  const nerfStr = nerfs.length ? `降：${nerfs.map(([k, v]) => fmt(k, v)).join('、')}` : ''
  return [buffStr, nerfStr].filter(Boolean).join('  ')
}

function addMember(team: TeamKey) {
  const t = teamRef(team)
  if (t.members.length >= 6) return
  t.members.push(emptyMember(t.members.length + 1))
}

function removeMember(team: TeamKey, index: number) {
  const t = teamRef(team)
  if (t.members.length <= 1) return
  t.members.splice(index, 1)
  t.members.forEach((m, i) => { m.sort_order = i + 1 })
}

const randomPkModesForPickerKeyword = computed(() => {
  const t = pickerKeyword.value.trim()
  if (!t) return randomPokemonModes.value
  return randomPokemonModes.value.filter((o) => o.label.includes(t))
})

function isMemberRandomLocked(m: MemberForm): boolean {
  return m.random_pk_dict_id !== null
}

function guardMemberEditable(team: TeamKey, mi: number): boolean {
  const m = teamRef(team).members[mi]
  if (m && isMemberRandomLocked(m)) {
    uni.showToast({ title: '随机精灵模式下仅可填写备注', icon: 'none' })
    return false
  }
  return true
}

// ── 弹层打开器 ─────────────────────────────────────────
function openPokemonPicker(team: TeamKey, mi: number) {
  pickerKind.value = 'pokemon'
  pickerCtx.value = { team, memberIndex: mi }
  pickerKeyword.value = ''
  pokemonHits.value = []
  pokemonSearchLoading.value = false
}

async function openSkillPicker(team: TeamKey, mi: number, si: number) {
  if (!guardMemberEditable(team, mi)) return
  const member = teamRef(team).members[mi]
  if (!member?.pokemon_name) {
    uni.showToast({ title: '请先选择精灵', icon: 'none' })
    return
  }
  pickerKind.value = 'skill'
  pickerCtx.value = { team, memberIndex: mi, skillIndex: si }
  pickerKeyword.value = ''
  skillHits.value = []
  selectedSkill.value = null
  skillAttrFilter.value = ''
  // 默认展示该精灵自己的技能列表
  skillSource.value = 'pet'
  petSkills.value = []
  pickerLoading.value = true
  try {
    const detail = await fetchPokemonDetail(member.pokemon_name)
    petSkills.value = detail.skills || []
  } catch {
    petSkills.value = []
  } finally {
    pickerLoading.value = false
  }
}

function openPersonalityPicker(team: TeamKey, mi: number) {
  if (!guardMemberEditable(team, mi)) return
  pickerKind.value = 'personality'
  pickerCtx.value = { team, memberIndex: mi }
}

function openBloodlinePicker(team: TeamKey, mi: number) {
  if (!guardMemberEditable(team, mi)) return
  pickerKind.value = 'bloodline'
  pickerCtx.value = { team, memberIndex: mi }
}

function openResonancePicker(team: TeamKey) {
  pickerKind.value = 'resonance'
  pickerCtx.value = { team, memberIndex: -1 }
}

function openQualPicker(team: TeamKey, mi: number, qualIndex: 1 | 2 | 3) {
  if (!guardMemberEditable(team, mi)) return
  pickerKind.value = 'qual'
  pickerCtx.value = { team, memberIndex: mi, qualIndex }
}

function closePicker() {
  pickerKind.value = 'none'
  pickerCtx.value = null
  pickerKeyword.value = ''
  pokemonHits.value = []
  pokemonSearchLoading.value = false
  skillHits.value = []
  selectedSkill.value = null
  skillAttrFilter.value = ''
  skillSource.value = 'pet'
  petSkills.value = []
}

// ── 搜索（精灵 / 技能） ───────────────────────────────
function onPickerKeywordInput(e: any) {
  pickerKeyword.value = (e.detail.value || '').trim()
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    if (pickerKind.value === 'pokemon') await runPokemonSearch()
    // 技能在 pet 模式下走本地过滤（visibleSkills 计算属性），无需发请求
    if (pickerKind.value === 'skill' && skillSource.value === 'search') await runSkillSearch()
  }, 280)
}

async function runPokemonSearch() {
  const kw = pickerKeyword.value.trim()
  if (!kw) {
    pokemonHits.value = []
    pokemonSearchLoading.value = false
    return
  }
  pokemonSearchLoading.value = true
  try {
    const res = await fetchPokemon({ name: kw, page: 1, page_size: 30 })
    pokemonHits.value = res.items
  } catch {
    pokemonHits.value = []
  } finally {
    pokemonSearchLoading.value = false
  }
}

async function runSkillSearch() {
  const kw = pickerKeyword.value.trim()
  const attr = skillAttrFilter.value
  // 关键字与属性筛选都为空时，避免一次拉全量技能
  if (!kw && !attr) {
    skillHits.value = []
    return
  }
  pickerLoading.value = true
  try {
    const res = await fetchSkills({ name: kw, attr })
    skillHits.value = res.items
  } catch {
    skillHits.value = []
  } finally {
    pickerLoading.value = false
  }
}

// attr 取值：null = 切回「本宠物」模式，'' = 「全部」搜索，其余 = 按属性搜索
function setSkillFilter(attr: string | null) {
  if (attr === null) {
    skillSource.value = 'pet'
    skillAttrFilter.value = ''
    skillHits.value = []
    return
  }
  skillSource.value = 'search'
  skillAttrFilter.value = attr
  void runSkillSearch()
}

// ── 选项确定 ──────────────────────────────────────────
function pickPokemon(item: Pokemon) {
  const ctx = pickerCtx.value
  if (!ctx) return
  const m = teamRef(ctx.team).members[ctx.memberIndex]
  if (!m) return
  m.random_pk_dict_id = null
  const idNum = Number(item.no)
  m.pokemon_id = Number.isFinite(idNum) ? idNum : null
  m.pokemon_name = item.name
  m.pokemon_image = item.image_url
  m.pokemon_attrs = (item.attributes || []).map((a) => a.attr_name)
  closePicker()
}

function selectSkillPreview(item: Skill) {
  // 仅高亮预览，不立即关闭弹层，避免点选时面板闪烁
  selectedSkill.value = item
}

function confirmSkillPick() {
  const ctx = pickerCtx.value
  const skill = selectedSkill.value
  if (!ctx || ctx.skillIndex === undefined || !skill) {
    uni.showToast({ title: '请先选择一个技能', icon: 'none' })
    return
  }
  const m = teamRef(ctx.team).members[ctx.memberIndex]
  if (!m || isMemberRandomLocked(m)) return
  m.skills[ctx.skillIndex] = { name: skill.name, image: skill.icon }
  closePicker()
}

function pickPersonality(p: PersonalityOption | null) {
  const ctx = pickerCtx.value
  if (!ctx) return
  const m = teamRef(ctx.team).members[ctx.memberIndex]
  if (!m || isMemberRandomLocked(m)) return
  m.personality_id = p?.id ?? null
  m.personality_name_zh = p?.name ?? ''
  closePicker()
}

function pickBloodline(b: BloodlineOption | null) {
  const ctx = pickerCtx.value
  if (!ctx) return
  const m = teamRef(ctx.team).members[ctx.memberIndex]
  if (!m || isMemberRandomLocked(m)) return
  m.random_pk_dict_id = null
  m.bloodline_dict_id = b?.id ?? null
  m.bloodline_label = b?.label ?? ''
  closePicker()
}

function normalizeAttrToken(s: string): string {
  return s.replace(/系$/u, '').trim()
}

/** 血脉标签（如「水系」）与 /api/attributes 的 attr_name 对齐，取属性图标 URL */
function attrImageUrlForBloodlineLabel(label: string): string {
  const attrs = attributes.value
  if (!label || !attrs.length) return ''
  const lb = label.trim()
  const lbNorm = normalizeAttrToken(lb)
  for (const a of attrs) {
    const name = a.attr_name.trim()
    const nameNorm = normalizeAttrToken(name)
    if (
      name === lb ||
      nameNorm === lbNorm ||
      lb.includes(name) ||
      name.includes(lbNorm)
    ) {
      return a.attr_image || ''
    }
  }
  return ''
}

function pickRandomPkOption(opt: BattlePkRandomPokemonOption) {
  const ctx = pickerCtx.value
  if (!ctx) return
  const m = teamRef(ctx.team).members[ctx.memberIndex]
  if (!m) return
  m.random_pk_dict_id = opt.id
  m.pokemon_id = null
  m.pokemon_name = opt.label
  m.pokemon_image = ''
  m.pokemon_attrs = []
  m.personality_id = null
  m.personality_name_zh = ''
  m.qual_1 = ''
  m.qual_2 = ''
  m.qual_3 = ''
  m.skills = [
    { name: '', image: '' },
    { name: '', image: '' },
    { name: '', image: '' },
    { name: '', image: '' },
  ]
  if (opt.kind === 'any') {
    m.bloodline_dict_id = null
    m.bloodline_label = ''
  } else if (opt.kind === 'attr' && opt.bloodline_code) {
    const bl = bloodlines.value.find((x) => x.code === opt.bloodline_code)
    if (bl) {
      m.bloodline_dict_id = bl.id
      m.bloodline_label = bl.label
      m.pokemon_image = attrImageUrlForBloodlineLabel(bl.label)
    }
  }
  closePicker()
}

function pickResonance(r: ResonanceMagicOption | null) {
  const ctx = pickerCtx.value
  if (!ctx) return
  const t = teamRef(ctx.team)
  t.resonance_magic_id = r?.id ?? null
  t.resonance_magic_name = r?.name ?? ''
  closePicker()
}

function pickQual(value: string) {
  const ctx = pickerCtx.value
  if (!ctx || ctx.qualIndex === undefined) return
  const m = teamRef(ctx.team).members[ctx.memberIndex]
  if (!m || isMemberRandomLocked(m)) return
  if (ctx.qualIndex === 1) m.qual_1 = value
  if (ctx.qualIndex === 2) m.qual_2 = value
  if (ctx.qualIndex === 3) m.qual_3 = value
  closePicker()
}

function onInputValue(setter: (v: string) => void) {
  return (e: any) => setter(e?.detail?.value ?? '')
}

function clearPokemon(team: TeamKey, mi: number) {
  const m = teamRef(team).members[mi]
  if (!m) return
  m.pokemon_id = null
  m.pokemon_name = ''
  m.pokemon_image = ''
  m.pokemon_attrs = []
  m.random_pk_dict_id = null
}

function clearSkill(team: TeamKey, mi: number, si: number) {
  if (!guardMemberEditable(team, mi)) return
  const m = teamRef(team).members[mi]
  if (!m) return
  m.skills[si] = { name: '', image: '' }
}

function statLabel(value: string) {
  return STAT_LABEL_MAP[value] || '未设置'
}

// ── 提交 ─────────────────────────────────────────────
function toPayload(team: TeamForm): BattlePkTeam {
  const members: BattlePkMember[] = team.members
    .filter((m) => m.pokemon_name.trim())
    .map((m, i) => ({
      pokemon_id: m.pokemon_id,
      pokemon_name: m.pokemon_name,
      sort_order: i + 1,
      bloodline_dict_id: m.bloodline_dict_id,
      bloodline_label: m.bloodline_label,
      personality_id: m.personality_id,
      personality_name_zh: m.personality_name_zh,
      qual_1: m.qual_1,
      qual_2: m.qual_2,
      qual_3: m.qual_3,
      skill_1_id: null,
      skill_1_name: m.skills[0]?.name || '',
      skill_2_id: null,
      skill_2_name: m.skills[1]?.name || '',
      skill_3_id: null,
      skill_3_name: m.skills[2]?.name || '',
      skill_4_id: null,
      skill_4_name: m.skills[3]?.name || '',
      member_desc: m.member_desc,
    }))
  return {
    title: team.title.trim() || '未命名队伍',
    lineup_desc: team.lineup_desc.trim(),
    source_type: 'user_pk',
    resonance_magic_id: team.resonance_magic_id,
    resonance_magic_name: team.resonance_magic_name,
    members,
  }
}

function validate(): string {
  const a = toPayload(teamA)
  const b = toPayload(teamB)
  if (!a.members.length) return '请至少为「我方队伍」配置 1 只精灵'
  if (!b.members.length) return '请至少为「对手队伍」配置 1 只精灵'
  for (const team of [
    { name: '我方', payload: a },
    { name: '对手', payload: b },
  ]) {
    for (const [i, m] of team.payload.members.entries()) {
      const stats = [m.qual_1, m.qual_2, m.qual_3].filter(Boolean)
      if (stats.length && new Set(stats).size !== stats.length) {
        return `${team.name}第 ${i + 1} 只精灵的资质不能重复`
      }
      const skillNames = [m.skill_1_name, m.skill_2_name, m.skill_3_name, m.skill_4_name].filter(Boolean)
      if (new Set(skillNames).size !== skillNames.length) {
        return `${team.name}第 ${i + 1} 只精灵的技能不能重复`
      }
    }
  }
  return ''
}

async function runBattle() {
  if (submitting.value) return
  const message = validate()
  if (message) {
    error.value = message
    uni.showToast({ title: message, icon: 'none' })
    return
  }
  submitting.value = true
  error.value = ''
  result.value = null
  uni.showLoading({ title: '正在模拟对战...', mask: true })
  try {
    const data = await submitBattlePk({
      team_a: toPayload(teamA),
      team_b: toPayload(teamB),
    })
    result.value = data
    uni.pageScrollTo({ selector: '.result-card', duration: 300 })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '分析失败，请稍后重试'
    uni.showToast({ title: error.value, icon: 'none' })
  } finally {
    submitting.value = false
    uni.hideLoading()
  }
}

function resetAll() {
  Object.assign(teamA, emptyTeam('我的队伍'))
  Object.assign(teamB, emptyTeam('对手队伍'))
  result.value = null
  error.value = ''
  activeTeam.value = 'A'
}

function winnerLabel(w: string): string {
  if (w === 'A') return '我方更优'
  if (w === 'B') return '对手更优'
  return '势均力敌'
}

onLoad(async () => {
  lineupLoading.value = true
  const [p, b, r, l, rm, attr] = await Promise.allSettled([
    fetchPersonalities(),
    fetchBloodlines(),
    fetchResonanceMagics(),
    fetchLineups(),
    fetchBattlePkRandomPokemonModes(),
    fetchAttributes(),
  ])
  if (p.status === 'fulfilled') personalities.value = p.value
  if (b.status === 'fulfilled') bloodlines.value = b.value
  if (r.status === 'fulfilled') resonanceMagics.value = r.value
  if (l.status === 'fulfilled') lineupOptions.value = l.value.items || []
  if (rm.status === 'fulfilled') randomPokemonModes.value = rm.value
  if (attr.status === 'fulfilled') attributes.value = attr.value
  lineupLoading.value = false
})
</script>

<template>
  <view class="page">
    <view class="hero-card">
      <text class="hero-title">阵容 PK</text>
      <text class="hero-subtitle">配置两套队伍，按经典回合制规则给出胜率与回合推演。</text>
    </view>

    <!-- 队伍切换 -->
    <view class="team-tabs">
      <view
        class="team-tab"
        :class="{ active: activeTeam === 'A' }"
        @tap="activeTeam = 'A'"
      >
        <text class="tab-tag a-tag">我方</text>
        <text class="tab-title">{{ teamA.title || '我的队伍' }}</text>
        <text class="tab-count">{{ teamA.members.filter(m => m.pokemon_name).length }}/6</text>
      </view>
      <view
        class="team-tab"
        :class="{ active: activeTeam === 'B' }"
        @tap="activeTeam = 'B'"
      >
        <text class="tab-tag b-tag">对手</text>
        <text class="tab-title">{{ teamB.title || '对手队伍' }}</text>
        <text class="tab-count">{{ teamB.members.filter(m => m.pokemon_name).length }}/6</text>
      </view>
    </view>

    <!-- 当前队伍配置 -->
    <view class="team-card">
      <view class="form-row">
        <text class="form-label">队伍名称</text>
        <input
          class="form-input"
          :value="teamRef(activeTeam).title"
          maxlength="20"
          placeholder="队伍名称"
          @input="onInputValue(v => teamRef(activeTeam).title = v)($event)"
        />
      </view>

      <view class="form-row">
        <text class="form-label">导入阵容</text>
        <view class="import-wrap">
          <picker
            mode="selector"
            :range="lineupOptions"
            range-key="title"
            :disabled="lineupLoading || !lineupOptions.length"
            @change="(e) => {
              const idx = Number(e?.detail?.value ?? -1)
              importLineupId[activeTeam] = idx >= 0 ? (lineupOptions[idx]?.id ?? null) : null
            }"
          >
            <view class="picker-box">
              <text class="picker-text">
                {{
                  lineupLoading
                    ? '加载阵容中...'
                    : (lineupOptions.find((l) => l.id === importLineupId[activeTeam])?.title || '点击选择已有阵容')
                }}
              </text>
              <text class="value-arrow">›</text>
            </view>
          </picker>
          <view class="import-btn" @tap="importPresetLineup(activeTeam)">一键导入</view>
        </view>
      </view>

      <view class="form-row" @tap="openResonancePicker(activeTeam)">
        <text class="form-label">共鸣魔法</text>
        <view class="form-value">
          <image
            v-if="teamRef(activeTeam).resonance_magic_id !== null && resonanceById.get(teamRef(activeTeam).resonance_magic_id!)?.icon_url"
            :src="resonanceById.get(teamRef(activeTeam).resonance_magic_id!)?.icon_url"
            class="resonance-icon"
            mode="aspectFit"
          />
          <text :class="['value-text', !teamRef(activeTeam).resonance_magic_name ? 'placeholder' : '']">
            {{ teamRef(activeTeam).resonance_magic_name || '未设置 / 点击选择' }}
          </text>
          <text class="value-arrow">›</text>
        </view>
      </view>

      <view
        v-if="teamRef(activeTeam).resonance_magic_id !== null && resonanceById.get(teamRef(activeTeam).resonance_magic_id!)?.description"
        class="resonance-hint"
      >
        {{ resonanceById.get(teamRef(activeTeam).resonance_magic_id!)?.description }}
      </view>

      <!-- 成员列表 -->
      <view
        v-for="(member, mi) in teamRef(activeTeam).members"
        :key="mi"
        class="pet-card"
      >
        <view class="pet-head">
          <view class="pet-head-left">
            <view class="pet-avatar">
              <image v-if="member.pokemon_image" :src="member.pokemon_image" mode="aspectFit" />
              <text v-else class="avatar-no">#{{ mi + 1 }}</text>
            </view>
            <view class="pet-title-wrap">
              <text class="pet-name">{{ member.pokemon_name || `精灵 ${mi + 1}` }}</text>
              <text class="pet-sub">第 {{ mi + 1 }} 只 · 上场顺序 {{ mi + 1 }}</text>
            </view>
          </view>
          <text
            v-if="teamRef(activeTeam).members.length > 1"
            class="remove-btn"
            @tap="removeMember(activeTeam, mi)"
          >
            移除
          </text>
        </view>

        <view class="form-row" @tap="openPokemonPicker(activeTeam, mi)">
          <text class="form-label">精灵</text>
          <view class="form-value">
            <image v-if="member.pokemon_image" :src="member.pokemon_image" class="value-img" mode="aspectFit" />
            <text :class="['value-text', !member.pokemon_name ? 'placeholder' : '']">
              {{ member.pokemon_name || '点击搜索精灵' }}
            </text>
            <text
              v-if="member.pokemon_name"
              class="value-clear"
              @tap.stop="clearPokemon(activeTeam, mi)"
            >×</text>
            <text v-else class="value-arrow">›</text>
          </view>
        </view>

        <view class="form-row" @tap="openPersonalityPicker(activeTeam, mi)">
          <text class="form-label">性格</text>
          <view class="form-value">
            <text :class="['value-text', !member.personality_name_zh ? 'placeholder' : '']">
              {{ member.personality_name_zh || '点击选择性格' }}
            </text>
            <text class="value-arrow">›</text>
          </view>
        </view>
        <view
          v-if="member.personality_id !== null && personalityById.get(member.personality_id)"
          class="hint"
        >ⓘ {{ personalityDesc(personalityById.get(member.personality_id!)!) }}</view>

        <view class="form-row" @tap="openBloodlinePicker(activeTeam, mi)">
          <text class="form-label">血脉</text>
          <view class="form-value">
            <text :class="['value-text', !member.bloodline_label ? 'placeholder' : '']">
              {{ member.bloodline_label || '点击选择血脉' }}
            </text>
            <text class="value-arrow">›</text>
          </view>
        </view>

        <view class="form-row">
          <text class="form-label">资质（不重复）</text>
          <view class="qual-grid">
            <view class="qual-cell" @tap="openQualPicker(activeTeam, mi, 1)">
              <text :class="['qual-text', !member.qual_1 ? 'placeholder' : '']">{{ member.qual_1 ? statLabel(member.qual_1) : '资质1' }}</text>
            </view>
            <view class="qual-cell" @tap="openQualPicker(activeTeam, mi, 2)">
              <text :class="['qual-text', !member.qual_2 ? 'placeholder' : '']">{{ member.qual_2 ? statLabel(member.qual_2) : '资质2' }}</text>
            </view>
            <view class="qual-cell" @tap="openQualPicker(activeTeam, mi, 3)">
              <text :class="['qual-text', !member.qual_3 ? 'placeholder' : '']">{{ member.qual_3 ? statLabel(member.qual_3) : '资质3' }}</text>
            </view>
          </view>
        </view>

        <view class="form-row column">
          <text class="form-label">技能（最多 4 个）</text>
          <view class="skill-grid">
            <view
              v-for="si in 4"
              :key="si"
              class="skill-cell"
              @tap="openSkillPicker(activeTeam, mi, si - 1)"
            >
              <image
                v-if="member.skills[si - 1]?.image"
                :src="member.skills[si - 1].image"
                class="skill-img"
                mode="aspectFit"
              />
              <text class="skill-cell-text">{{ member.skills[si - 1]?.name || `技能 ${si}` }}</text>
              <text
                v-if="member.skills[si - 1]?.name && member.random_pk_dict_id === null"
                class="value-clear"
                @tap.stop="clearSkill(activeTeam, mi, si - 1)"
              >×</text>
            </view>
          </view>
        </view>

        <view class="form-row column">
          <text class="form-label">该精灵备注（可选）</text>
          <textarea
            class="form-textarea"
            :value="member.member_desc"
            placeholder="例如：核心输出 / 工具人 / 联防替补..."
            @input="onInputValue(v => member.member_desc = v)($event)"
          />
        </view>
      </view>

      <view
        v-if="teamRef(activeTeam).members.length < 6"
        class="add-member-btn"
        @tap="addMember(activeTeam)"
      >+ 添加精灵（最多 6 只）</view>

      <view class="form-row column">
        <text class="form-label">队伍说明（可选）</text>
        <textarea
          class="form-textarea"
          :value="teamRef(activeTeam).lineup_desc"
          placeholder="整体打法描述，如高速压制 / 消耗联防..."
          @input="onInputValue(v => teamRef(activeTeam).lineup_desc = v)($event)"
        />
      </view>
    </view>

    <view class="action-bar">
      <view class="btn-primary" @tap="runBattle">开始 PK</view>
      <view class="btn-default" @tap="resetAll">重置</view>
    </view>

    <view v-if="error" class="error-box">{{ error }}</view>

    <!-- 结果 -->
    <view v-if="result" class="result-card">
      <view v-if="result.error" class="error-box">
        AI 输出解析失败：{{ result.error }}
      </view>
      <template v-else>
        <view
          v-if="result.completeness && !result.completeness.ok && result.completeness.missing?.length"
          class="warn-box"
        >
          数据不完整：{{ result.completeness.missing.join('；') }}
        </view>

        <view class="verdict">
          <view class="verdict-row">
            <text :class="['verdict-tag', `tag-${result.verdict.winner.toLowerCase()}`]">
              {{ winnerLabel(result.verdict.winner) }}
            </text>
            <text class="verdict-rate">我方 {{ result.verdict.win_rate_a }}% · 对手 {{ 100 - result.verdict.win_rate_a }}%</text>
          </view>
          <text class="verdict-reason">{{ result.verdict.reason }}</text>
          <view class="bar">
            <view class="bar-a" :style="{ width: result.verdict.win_rate_a + '%' }" />
            <view class="bar-b" :style="{ width: (100 - result.verdict.win_rate_a) + '%' }" />
          </view>
        </view>

        <view v-if="result.plan" class="plan-card">
          <text class="plan-title">AI 推荐的最优出战计划</text>

          <view class="plan-order plan-a">
            <text class="plan-tag a-tag">我方 最优顺序</text>
            <view class="plan-chain">
              <template v-for="(name, i) in result.plan.team_a_order" :key="`oa-${i}`">
                <text class="chain-node a-node">{{ name }}</text>
                <text v-if="i < result.plan.team_a_order.length - 1" class="chain-arrow">›</text>
              </template>
            </view>
            <text v-if="result.plan.team_a_order_reason" class="plan-reason">{{ result.plan.team_a_order_reason }}</text>
          </view>

          <view class="plan-order plan-b">
            <text class="plan-tag b-tag">对手 最优顺序</text>
            <view class="plan-chain">
              <template v-for="(name, i) in result.plan.team_b_order" :key="`ob-${i}`">
                <text class="chain-node b-node">{{ name }}</text>
                <text v-if="i < result.plan.team_b_order.length - 1" class="chain-arrow">›</text>
              </template>
            </view>
            <text v-if="result.plan.team_b_order_reason" class="plan-reason">{{ result.plan.team_b_order_reason }}</text>
          </view>

          <view v-if="result.plan.skill_matchup?.length" class="plan-section">
            <text class="plan-sub">技能应对关系</text>
            <view v-for="(s, i) in result.plan.skill_matchup" :key="`sm-${i}`" class="plan-item">· {{ s }}</view>
          </view>

          <view v-if="result.plan.ability_impact?.length" class="plan-section">
            <text class="plan-sub">特性 / 共鸣魔法 影响</text>
            <view v-for="(s, i) in result.plan.ability_impact" :key="`ai-${i}`" class="plan-item">· {{ s }}</view>
          </view>
        </view>

        <view class="side-block">
          <text class="side-title">我方 · {{ result.team_a.summary }}</text>
          <text class="side-sub">优势</text>
          <view v-for="(s, i) in result.team_a.advantages" :key="`aa-${i}`" class="side-item">· {{ s }}</view>
          <text class="side-sub">风险</text>
          <view v-for="(s, i) in result.team_a.weaknesses" :key="`aw-${i}`" class="side-item muted">· {{ s }}</view>
        </view>

        <view class="side-block">
          <text class="side-title">对手 · {{ result.team_b.summary }}</text>
          <text class="side-sub">优势</text>
          <view v-for="(s, i) in result.team_b.advantages" :key="`ba-${i}`" class="side-item">· {{ s }}</view>
          <text class="side-sub">风险</text>
          <view v-for="(s, i) in result.team_b.weaknesses" :key="`bw-${i}`" class="side-item muted">· {{ s }}</view>
        </view>

        <view class="rounds">
          <text class="side-title">关键回合推演</text>
          <view v-for="r in result.key_rounds" :key="r.round" class="round-item">
            <text class="round-tag">R{{ r.round }}</text>
            <text class="round-desc">{{ r.desc }}</text>
          </view>
        </view>

        <view v-if="result.turning_points?.length" class="rounds">
          <text class="side-title">翻盘点</text>
          <view v-for="(t, i) in result.turning_points" :key="`tp-${i}`" class="side-item">· {{ t }}</view>
        </view>
      </template>
    </view>

    <!-- 弹层 -->
    <view v-if="pickerKind !== 'none'" class="picker-mask" @tap="closePicker">
      <view class="picker-sheet" @tap.stop>
        <view class="picker-head">
          <text class="picker-title">
            <template v-if="pickerKind === 'pokemon'">选择精灵</template>
            <template v-else-if="pickerKind === 'skill'">选择技能</template>
            <template v-else-if="pickerKind === 'personality'">选择性格</template>
            <template v-else-if="pickerKind === 'bloodline'">选择血脉</template>
            <template v-else-if="pickerKind === 'resonance'">选择共鸣魔法</template>
            <template v-else-if="pickerKind === 'qual'">选择资质</template>
          </text>
          <text class="picker-close" @tap="closePicker">×</text>
        </view>

        <!-- 搜索类（精灵） -->
        <template v-if="pickerKind === 'pokemon'">
          <view class="picker-search">
            <input
              class="picker-search-input"
              :value="pickerKeyword"
              placeholder="输入精灵名称"
              @input="onPickerKeywordInput"
            />
          </view>
          <scroll-view class="picker-list" scroll-y>
            <view
              v-for="opt in randomPkModesForPickerKeyword"
              :key="`rand-${opt.id}`"
              class="picker-item"
              @tap="pickRandomPkOption(opt)"
            >
              <text class="picker-item-text">{{ opt.label }}</text>
            </view>
            <template v-if="pickerKeyword.trim()">
              <view v-if="pokemonSearchLoading" class="picker-tip">搜索中...</view>
              <template v-else>
                <view
                  v-for="opt in pokemonHits"
                  :key="opt.no"
                  class="picker-item"
                  @tap="pickPokemon(opt)"
                >
                  <image v-if="opt.image_url" :src="opt.image_url" class="picker-img" mode="aspectFit" />
                  <text class="picker-item-text">{{ opt.name }}</text>
                </view>
                <view v-if="!pokemonHits.length" class="picker-tip">没有匹配的精灵</view>
              </template>
            </template>
            <view
              v-else-if="!randomPkModesForPickerKeyword.length"
              class="picker-tip"
            >暂无随机选项，请先在后端 seed 字典</view>
          </scroll-view>
        </template>

        <!-- 技能：固定区域滑动浏览 + 预览 + 确认 -->
        <template v-else-if="pickerKind === 'skill'">
          <view class="picker-search">
            <input
              class="picker-search-input"
              :value="pickerKeyword"
              placeholder="输入技能名称（可选）"
              @input="onPickerKeywordInput"
            />
          </view>
          <scroll-view class="skill-attr-bar" scroll-x>
            <view class="skill-attr-row">
              <view
                class="skill-attr-chip"
                :class="{ active: skillSource === 'pet' }"
                @tap="setSkillFilter(null)"
              >本宠物</view>
              <view
                class="skill-attr-chip"
                :class="{ active: skillSource === 'search' && skillAttrFilter === '' }"
                @tap="setSkillFilter('')"
              >全部</view>
              <view
                v-for="attr in skillPickerAttrs"
                :key="attr"
                class="skill-attr-chip"
                :class="{ active: skillSource === 'search' && skillAttrFilter === attr }"
                @tap="setSkillFilter(attr)"
              >{{ attr }}</view>
            </view>
          </scroll-view>
          <scroll-view class="skill-picker-list" scroll-y>
            <view v-if="pickerLoading" class="picker-tip">加载中...</view>
            <template v-else>
              <view
                v-for="opt in visibleSkills"
                :key="opt.name"
                class="skill-item"
                :class="{ active: selectedSkill && selectedSkill.name === opt.name }"
                @tap="selectSkillPreview(opt)"
              >
                <image v-if="opt.icon" :src="opt.icon" class="skill-item-icon" mode="aspectFit" />
                <view class="skill-item-body">
                  <view class="skill-item-row">
                    <text class="skill-item-name">{{ opt.name }}</text>
                    <text class="skill-item-tag">{{ opt.attr || '—' }}</text>
                  </view>
                  <text class="skill-item-meta">{{ opt.type || '—' }} · 威力 {{ opt.power || 0 }} · 消耗 {{ opt.consume || 0 }}</text>
                  <text v-if="opt.desc" class="skill-item-desc">{{ opt.desc }}</text>
                </view>
                <text class="skill-item-check">{{ selectedSkill && selectedSkill.name === opt.name ? '✓' : '' }}</text>
              </view>
              <template v-if="!visibleSkills.length">
                <view v-if="skillSource === 'pet' && pickerKeyword" class="picker-tip">该精灵的技能中没有匹配「{{ pickerKeyword }}」的</view>
                <view v-else-if="skillSource === 'pet'" class="picker-tip">该精灵暂无技能数据，可点击「全部」或属性 chip 浏览</view>
                <view v-else-if="pickerKeyword || skillAttrFilter" class="picker-tip">没有匹配的技能</view>
                <view v-else class="picker-tip">点击上方筛选项或输入关键词开始浏览</view>
              </template>
            </template>
          </scroll-view>

          <view class="skill-preview" v-if="selectedSkill">
            <view class="skill-preview-head">
              <image v-if="selectedSkill.icon" :src="selectedSkill.icon" class="skill-preview-icon" mode="aspectFit" />
              <view class="skill-preview-title-wrap">
                <text class="skill-preview-title">已选：{{ selectedSkill.name }}</text>
                <text class="skill-preview-meta">{{ selectedSkill.attr || '—' }} · {{ selectedSkill.type || '—' }} · 威力 {{ selectedSkill.power || 0 }} · 消耗 {{ selectedSkill.consume || 0 }}</text>
              </view>
            </view>
            <text class="skill-preview-desc">{{ selectedSkill.desc || '暂无技能描述' }}</text>
          </view>
          <view class="skill-preview empty" v-else>
            <text class="skill-preview-empty">点击列表中的技能查看描述并预选</text>
          </view>

          <view class="picker-foot">
            <view class="picker-foot-btn cancel" @tap="closePicker">取消</view>
            <view
              class="picker-foot-btn confirm"
              :class="{ disabled: !selectedSkill }"
              @tap="confirmSkillPick"
            >确认选择</view>
          </view>
        </template>

        <!-- 性格 -->
        <scroll-view v-else-if="pickerKind === 'personality'" class="picker-list" scroll-y>
          <view class="picker-item" @tap="pickPersonality(null)">
            <view class="picker-item-content">
              <text class="picker-item-text">未设置</text>
            </view>
          </view>
          <view
            v-for="p in personalities"
            :key="p.id"
            class="picker-item"
            @tap="pickPersonality(p)"
          >
            <view class="picker-item-content">
              <text class="picker-item-text">{{ p.name }}</text>
              <text class="picker-item-sub">{{ personalityDesc(p) }}</text>
            </view>
          </view>
        </scroll-view>

        <!-- 血脉 -->
        <scroll-view v-else-if="pickerKind === 'bloodline'" class="picker-list" scroll-y>
          <view class="picker-item" @tap="pickBloodline(null)">
            <text class="picker-item-text">未设置</text>
          </view>
          <view
            v-for="b in bloodlines"
            :key="b.id"
            class="picker-item"
            @tap="pickBloodline(b)"
          >
            <text class="picker-item-text">{{ b.label }}</text>
          </view>
        </scroll-view>

        <!-- 共鸣魔法 -->
        <scroll-view v-else-if="pickerKind === 'resonance'" class="picker-list" scroll-y>
          <view class="picker-item" @tap="pickResonance(null)">
            <view class="picker-item-content">
              <text class="picker-item-text">未设置</text>
            </view>
          </view>
          <view
            v-for="m in resonanceMagics"
            :key="m.id"
            class="picker-item"
            @tap="pickResonance(m)"
          >
            <image v-if="m.icon_url" :src="m.icon_url" class="picker-img" mode="aspectFit" />
            <view class="picker-item-content">
              <text class="picker-item-text">{{ m.name }}</text>
              <text class="picker-item-sub">{{ m.description }}</text>
            </view>
          </view>
        </scroll-view>

        <!-- 资质 -->
        <scroll-view v-else-if="pickerKind === 'qual'" class="picker-list" scroll-y>
          <view class="picker-item" @tap="pickQual('')">
            <text class="picker-item-text">未设置</text>
          </view>
          <view
            v-for="opt in STAT_OPTIONS"
            :key="opt.value"
            class="picker-item"
            @tap="pickQual(opt.value)"
          >
            <text class="picker-item-text">{{ opt.label }}</text>
          </view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 24rpx 24rpx 120rpx;
  background: linear-gradient(180deg, #f3f8ff 0%, #f9fbff 100%);
}

.hero-card {
  margin-bottom: 24rpx;
  padding: 32rpx 28rpx;
  border-radius: 28rpx;
  background: linear-gradient(135deg, #2b74ff 0%, #f56c6c 100%);
  box-shadow: 0 12rpx 32rpx rgba(43, 116, 255, 0.2);
}
.hero-title { display: block; font-size: 38rpx; font-weight: 700; color: #fff; }
.hero-subtitle { display: block; margin-top: 10rpx; font-size: 24rpx; color: rgba(255,255,255,0.8); line-height: 1.6; }

.team-tabs {
  display: flex; gap: 12rpx;
  margin-bottom: 16rpx;
}
.team-tab {
  flex: 1; padding: 18rpx 16rpx;
  border-radius: 20rpx; background: #fff;
  display: flex; flex-direction: column; gap: 4rpx;
  border: 2rpx solid transparent;
}
.team-tab.active { border-color: #2b74ff; box-shadow: 0 8rpx 18rpx rgba(43, 116, 255, 0.18); }
.tab-tag {
  align-self: flex-start;
  padding: 2rpx 12rpx; border-radius: 10rpx;
  font-size: 20rpx; color: #fff;
}
.a-tag { background: #2b74ff; }
.b-tag { background: #f56c6c; }
.tab-title { font-size: 26rpx; font-weight: 600; color: #1f3760; }
.tab-count { font-size: 22rpx; color: #7a93bb; }

.team-card {
  border-radius: 28rpx; background: #fff;
  padding: 20rpx; margin-bottom: 24rpx;
  box-shadow: 0 8rpx 24rpx rgba(64, 125, 255, 0.06);
}

.form-row {
  display: flex; align-items: center;
  gap: 16rpx; padding: 16rpx 0;
  border-bottom: 1rpx solid #f0f4fb;
}
.form-row:last-child { border-bottom: none; }
.form-row.column { flex-direction: column; align-items: stretch; gap: 10rpx; }
.form-label {
  flex: 0 0 auto; min-width: 140rpx;
  font-size: 26rpx; color: #5b7299;
}
.form-input {
  flex: 1; min-width: 0;
  font-size: 28rpx; color: #1f3760;
  padding: 6rpx 0;
  text-align: right;
}
.import-wrap {
  flex: 1; min-width: 0;
  display: flex; align-items: center; gap: 12rpx;
}
.picker-box {
  flex: 1; min-width: 0;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 18rpx;
  height: 68rpx;
  border-radius: 14rpx;
  background: #f3f8ff;
}
.picker-text {
  flex: 1; min-width: 0;
  font-size: 24rpx; color: #1f3760;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.import-btn {
  flex: 0 0 auto;
  padding: 0 18rpx;
  height: 68rpx; line-height: 68rpx;
  border-radius: 14rpx;
  background: #ecf5ff;
  color: #2b74ff;
  font-size: 24rpx;
}
.form-value {
  flex: 1; min-width: 0;
  display: flex; align-items: center; justify-content: flex-end;
  gap: 10rpx;
}
.value-text { font-size: 28rpx; color: #1f3760; flex: 1; text-align: right;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.value-text.placeholder { color: #b3c1da; }
.value-arrow { font-size: 32rpx; color: #b5c8e8; }
.value-img { width: 56rpx; height: 56rpx; }
.value-clear {
  width: 36rpx; height: 36rpx; line-height: 36rpx;
  text-align: center; border-radius: 50%;
  background: #f3f5f9; color: #909bb0; font-size: 24rpx;
}
.resonance-icon { width: 44rpx; height: 44rpx; }
.resonance-hint {
  margin-top: 4rpx; padding: 10rpx 14rpx;
  background: #fff7eb; border-radius: 14rpx;
  font-size: 22rpx; color: #b88230; line-height: 1.5;
}

.pet-card {
  margin-top: 16rpx;
  padding: 16rpx;
  border-radius: 22rpx;
  background: linear-gradient(135deg, #f6faff 0%, #ffffff 100%);
  border: 1rpx solid #eef3fb;
}
.pet-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8rpx;
}
.pet-head-left { display: flex; align-items: center; gap: 12rpx; }
.pet-avatar {
  width: 72rpx; height: 72rpx; border-radius: 16rpx;
  background: #fff; border: 1rpx solid #eef3fb;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
}
.pet-avatar image { width: 100%; height: 100%; }
.avatar-no { font-size: 22rpx; color: #b5c8e8; }
.pet-title-wrap { display: flex; flex-direction: column; gap: 4rpx; }
.pet-name { font-size: 28rpx; font-weight: 600; color: #1f3760; }
.pet-sub { font-size: 22rpx; color: #7a93bb; }
.remove-btn {
  font-size: 24rpx; color: #f56c6c;
  padding: 4rpx 12rpx;
}

.hint {
  margin: -8rpx 0 8rpx; padding-left: 140rpx;
  font-size: 22rpx; color: #7a93bb; line-height: 1.5;
}

.qual-grid {
  flex: 1; display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 8rpx;
}
.qual-cell {
  padding: 12rpx 8rpx; border-radius: 12rpx;
  background: #f3f8ff; text-align: center;
}
.qual-text { font-size: 24rpx; color: #1f3760; }
.qual-text.placeholder { color: #b3c1da; }

.skill-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 10rpx;
}
.skill-cell {
  display: flex; align-items: center; gap: 8rpx;
  padding: 12rpx 12rpx; border-radius: 14rpx;
  background: #f3f8ff;
  position: relative;
}
.skill-img { width: 40rpx; height: 40rpx; }
.skill-cell-text {
  flex: 1; font-size: 24rpx; color: #1f3760;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.form-textarea {
  width: 100%; min-height: 120rpx;
  padding: 14rpx 16rpx;
  border-radius: 14rpx; background: #f6faff;
  font-size: 26rpx; color: #1f3760; line-height: 1.5;
  box-sizing: border-box;
}

.add-member-btn {
  margin-top: 16rpx; padding: 18rpx 0;
  text-align: center; border-radius: 16rpx;
  background: #ecf5ff; color: #2b74ff;
  font-size: 26rpx;
}

.action-bar {
  display: flex; gap: 16rpx; margin-bottom: 24rpx;
}
.btn-primary, .btn-default {
  flex: 1; height: 88rpx; line-height: 88rpx;
  text-align: center; border-radius: 20rpx;
  font-size: 30rpx; font-weight: 600;
}
.btn-primary { background: linear-gradient(135deg, #2b74ff, #f56c6c); color: #fff; }
.btn-default { background: #fff; color: #5b7299; border: 1rpx solid #dde6f4; }

.error-box {
  margin-bottom: 24rpx; padding: 18rpx;
  border-radius: 16rpx; background: #fef0f0; color: #c45656;
  font-size: 24rpx; line-height: 1.5;
}
.warn-box {
  margin-bottom: 16rpx; padding: 14rpx; border-radius: 14rpx;
  background: #fff7eb; color: #b88230; font-size: 22rpx;
}

.result-card {
  background: #fff; border-radius: 28rpx;
  padding: 24rpx; box-shadow: 0 8rpx 24rpx rgba(64, 125, 255, 0.06);
}
.verdict { padding-bottom: 18rpx; border-bottom: 1rpx solid #f0f4fb; margin-bottom: 18rpx; }
.verdict-row { display: flex; align-items: center; gap: 14rpx; flex-wrap: wrap; }
.verdict-tag {
  padding: 4rpx 16rpx; border-radius: 16rpx;
  font-size: 24rpx; font-weight: 600;
}
.tag-a { background: #ecf5ff; color: #2b74ff; }
.tag-b { background: #fef0f0; color: #f56c6c; }
.tag-draw { background: #f4f4f5; color: #909399; }
.verdict-rate { font-size: 26rpx; font-weight: 600; color: #1f3760; }
.verdict-reason { display: block; margin: 12rpx 0 14rpx; font-size: 24rpx; color: #5b7299; line-height: 1.6; }
.bar { display: flex; height: 18rpx; border-radius: 9rpx; overflow: hidden; background: #f0f4fb; }
.bar-a { background: linear-gradient(90deg, #2b74ff, #66a3ff); }
.bar-b { background: linear-gradient(90deg, #f78989, #f56c6c); }

.plan-card {
  margin-bottom: 18rpx;
  padding: 18rpx;
  border-radius: 18rpx;
  background: linear-gradient(135deg, #f3f8ff 0%, #fff5f5 100%);
  border: 1rpx solid #e3ecfb;
}
.plan-title { display: block; margin-bottom: 14rpx; font-size: 28rpx; font-weight: 600; color: #1f3760; }
.plan-order { padding: 14rpx; border-radius: 14rpx; background: #ffffff; margin-bottom: 12rpx; }
.plan-tag {
  display: inline-block; padding: 4rpx 16rpx;
  border-radius: 14rpx; font-size: 22rpx; font-weight: 600; color: #fff;
  margin-bottom: 10rpx;
}
.plan-tag.a-tag { background: #2b74ff; }
.plan-tag.b-tag { background: #f56c6c; }
.plan-chain { display: flex; flex-wrap: wrap; align-items: center; gap: 8rpx; }
.chain-node {
  padding: 6rpx 16rpx; border-radius: 16rpx;
  font-size: 24rpx; font-weight: 600;
  background: #f3f8ff; border: 1rpx solid #d8e6fa;
}
.chain-node.a-node { color: #2b74ff; }
.chain-node.b-node { color: #f56c6c; background: #fef0f0; border-color: #fbd9d9; }
.chain-arrow { color: #b5c8e8; font-size: 26rpx; }
.plan-reason { display: block; margin-top: 10rpx; font-size: 22rpx; color: #5b7299; line-height: 1.6; }

.plan-section { margin-top: 12rpx; }
.plan-sub { display: block; margin-bottom: 6rpx; font-size: 22rpx; color: #7a93bb; }
.plan-item { font-size: 24rpx; color: #1f3760; line-height: 1.7; }

.side-block { margin-bottom: 18rpx; }
.side-title { display: block; font-size: 28rpx; font-weight: 600; color: #1f3760; margin-bottom: 8rpx; }
.side-sub { display: block; margin: 12rpx 0 6rpx; font-size: 22rpx; color: #7a93bb; }
.side-item { font-size: 24rpx; color: #1f3760; line-height: 1.7; }
.side-item.muted { color: #7a93bb; }

.rounds { margin-top: 18rpx; padding-top: 18rpx; border-top: 1rpx solid #f0f4fb; }
.round-item {
  display: flex; gap: 12rpx;
  padding: 14rpx 16rpx; border-radius: 14rpx;
  background: #f3f8ff; margin-bottom: 10rpx;
}
.round-tag {
  flex: 0 0 auto; padding: 0 12rpx; height: 36rpx; line-height: 36rpx;
  border-radius: 18rpx; background: #2b74ff; color: #fff;
  font-size: 22rpx; font-weight: 600;
}
.round-desc { flex: 1; font-size: 24rpx; color: #1f3760; line-height: 1.6; }

/* 弹层 */
.picker-mask {
  position: fixed; inset: 0;
  background: rgba(15, 23, 42, 0.36);
  z-index: 99;
  display: flex; align-items: flex-end;
}
.picker-sheet {
  width: 100%; max-height: 86vh;
  background: #fff;
  border-top-left-radius: 28rpx; border-top-right-radius: 28rpx;
  display: flex; flex-direction: column;
  overflow: hidden;
}
.picker-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 24rpx; border-bottom: 1rpx solid #f0f4fb;
}
.picker-title { font-size: 30rpx; font-weight: 600; color: #1f3760; }
.picker-close { font-size: 40rpx; color: #909bb0; padding: 0 16rpx; }
.picker-search { padding: 16rpx 24rpx; }
.picker-search-input {
  height: 72rpx; padding: 0 20rpx;
  border-radius: 36rpx; background: #f3f8ff;
  font-size: 26rpx; color: #1f3760;
}
.picker-list { flex: 1; max-height: 65vh; }
.picker-item {
  display: flex; align-items: center; gap: 14rpx;
  padding: 22rpx 24rpx;
  border-bottom: 1rpx solid #f6f9fd;
}
.picker-item-content { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4rpx; }
.picker-item-text { font-size: 28rpx; color: #1f3760; }
.picker-item-sub { font-size: 22rpx; color: #7a93bb; line-height: 1.4; }
.picker-img { width: 56rpx; height: 56rpx; }
.picker-tip {
  padding: 60rpx 0; text-align: center;
  font-size: 24rpx; color: #b5c8e8;
}

/* 技能选择器：固定区域滑动浏览 + 预览 + 确认 */
.skill-attr-bar {
  flex: 0 0 auto;
  white-space: nowrap;
  padding: 0 24rpx 12rpx;
  border-bottom: 1rpx solid #f0f4fb;
}
.skill-attr-row {
  display: inline-flex; align-items: center; gap: 12rpx;
}
.skill-attr-chip {
  padding: 10rpx 22rpx;
  border-radius: 999rpx;
  background: #f3f8ff;
  color: #45638e;
  font-size: 24rpx;
  white-space: nowrap;
}
.skill-attr-chip.active {
  background: linear-gradient(135deg, #2b74ff 0%, #53a0ff 100%);
  color: #ffffff;
}

.skill-picker-list {
  flex: 1 1 auto;
  min-height: 280rpx;
  max-height: 42vh;      /* 固定范围，避免高度抖动导致闪烁 */
  background: #fafcff;
}
.skill-item {
  display: flex;
  align-items: flex-start;
  gap: 14rpx;
  padding: 18rpx 24rpx;
  border-bottom: 1rpx solid #f0f4fb;
  background: #ffffff;
}
.skill-item.active {
  background: linear-gradient(135deg, #ecf5ff 0%, #ffffff 100%);
  border-left: 6rpx solid #2b74ff;
  padding-left: 18rpx;
}
.skill-item-icon {
  width: 64rpx; height: 64rpx;
  flex: 0 0 auto;
  border-radius: 14rpx;
  background: #f3f8ff;
}
.skill-item-body {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; gap: 6rpx;
}
.skill-item-row {
  display: flex; align-items: center; gap: 10rpx;
}
.skill-item-name {
  font-size: 28rpx; font-weight: 600; color: #1f3760;
}
.skill-item-tag {
  padding: 2rpx 12rpx; border-radius: 10rpx;
  background: #ecf5ff; color: #2b74ff;
  font-size: 20rpx;
}
.skill-item-meta {
  font-size: 22rpx; color: #7a93bb;
}
.skill-item-desc {
  font-size: 22rpx; color: #5b7299;
  line-height: 1.5;
  word-break: break-all;
}
.skill-item-check {
  flex: 0 0 auto;
  width: 36rpx; min-width: 36rpx;
  font-size: 30rpx; font-weight: 700;
  color: #2b74ff; text-align: center;
}

.skill-preview {
  flex: 0 0 auto;
  padding: 18rpx 24rpx;
  border-top: 1rpx solid #f0f4fb;
  background: #ffffff;
}
.skill-preview.empty { padding: 22rpx 24rpx; }
.skill-preview-empty { font-size: 24rpx; color: #b5c8e8; }
.skill-preview-head {
  display: flex; align-items: center; gap: 12rpx;
  margin-bottom: 8rpx;
}
.skill-preview-icon {
  width: 56rpx; height: 56rpx; border-radius: 12rpx;
  background: #f3f8ff;
}
.skill-preview-title-wrap {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; gap: 4rpx;
}
.skill-preview-title { font-size: 26rpx; font-weight: 600; color: #1f3760; }
.skill-preview-meta { font-size: 22rpx; color: #7a93bb; }
.skill-preview-desc {
  display: block;
  margin-top: 4rpx;
  padding: 12rpx 14rpx;
  background: #f6faff;
  border-radius: 12rpx;
  font-size: 24rpx; color: #1f3760;
  line-height: 1.6;
  word-break: break-all;
}

.picker-foot {
  flex: 0 0 auto;
  display: flex; gap: 16rpx;
  padding: 18rpx 24rpx 24rpx;
  border-top: 1rpx solid #f0f4fb;
  background: #ffffff;
}
.picker-foot-btn {
  flex: 1;
  height: 84rpx; line-height: 84rpx;
  text-align: center; border-radius: 18rpx;
  font-size: 28rpx; font-weight: 600;
}
.picker-foot-btn.cancel {
  background: #f3f8ff; color: #5b7299;
}
.picker-foot-btn.confirm {
  background: linear-gradient(135deg, #2b74ff, #f56c6c);
  color: #ffffff;
}
.picker-foot-btn.confirm.disabled {
  opacity: 0.5;
}
</style>
