<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { fetchAttributes, fetchBattlePkRandomPokemonModes } from '@/api/pokemon'
import {
  clearOpsToken,
  createOpsPokemonLineup,
  deleteOpsPokemonLineup,
  fetchOpsDicts,
  fetchOpsMe,
  fetchOpsPersonalities,
  fetchOpsPokemonLineup,
  fetchOpsPokemonLineups,
  fetchOpsResonanceMagics,
  searchPokemonLineupPokemon,
  searchPokemonLineupSkills,
  showOpsToast,
  updateOpsPokemonLineup,
  type OpsDictItem,
  type OpsPersonalityItem,
  type OpsPersonalityStat,
  type OpsPokemonLineupListItem,
  type OpsResonanceMagicItem,
  type OpsPokemonLineupSearchItem,
  type OpsPokemonLineupStatKey,
} from '@/api/ops'
import type { Attribute, BattlePkRandomPokemonOption } from '@/types'

type StatKey = OpsPokemonLineupStatKey | ''

interface MemberForm {
  pokemon_id: number | null
  /** sys_dict battle_pk_random_pokemon */
  random_pk_dict_id: number | null
  pokemon_name: string
  pokemon_image: string
  sort_order: number
  bloodline_dict_id: number | null
  personality_id: number | null
  qual_1: StatKey
  qual_2: StatKey
  qual_3: StatKey
  skills: Array<{ id: number | null; name: string; image: string }>
  member_desc: string
}

const STAT_DICT_TYPE = 'pokemon_stat'
const BLOODLINE_DICT_TYPE = 'pet_bloodline'
const LINEUP_TYPE_DICT = 'pokemon_lineup_type'
/** 与 sys_dict 中阵容分类 label「闪耀大赛」对应（按 label 识别，code 可为任意合法值） */
const SHINING_LINEUP_LABEL = '闪耀大赛'

const PERSONALITY_MOD_COL: Record<OpsPersonalityStat, keyof OpsPersonalityItem> = {
  hp: 'hp_mod_pct',
  phy_atk: 'phy_atk_mod_pct',
  mag_atk: 'mag_atk_mod_pct',
  phy_def: 'phy_def_mod_pct',
  mag_def: 'mag_def_mod_pct',
  spd: 'spd_mod_pct',
}

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const items = ref<OpsPokemonLineupListItem[]>([])
const editingId = ref<number | null>(null)
const drawerVisible = ref(false)
const currentPage = ref(1)
const pageSize = 10
const total = ref(0)
const isAdmin = ref(false)

const statOptions = ref<Array<{ value: OpsPokemonLineupStatKey; label: string }>>([])
const bloodlineOptions = ref<OpsDictItem[]>([])
const personalityOptions = ref<OpsPersonalityItem[]>([])
const lineupTypeOptions = ref<OpsDictItem[]>([])
const resonanceMagicOptions = ref<OpsResonanceMagicItem[]>([])
const randomPokemonModes = ref<BattlePkRandomPokemonOption[]>([])
const attributes = ref<Attribute[]>([])

const keyword = ref('')
const sourceTypeFilter = ref('')
const isActiveFilter = ref<'' | 'true' | 'false'>('')

const form = reactive({
  title: '',
  lineup_desc: '',
  source_type: '',
  resonance_magic_id: null as number | null,
  sort_order: 1,
  is_active: true,
  members: [] as MemberForm[],
})

/** 当前分类是否为字典里的「闪耀大赛」（必须 6 只） */
const requiresSixSlotsLineup = computed(() => {
  const st = String(form.source_type ?? '').trim()
  if (!st) return false
  const hit = lineupTypeOptions.value.find((o) => String(o.code ?? '').trim() === st)
  return (hit?.label ?? '').trim() === SHINING_LINEUP_LABEL
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const pageStart = computed(() => (total.value === 0 ? 0 : (currentPage.value - 1) * pageSize + 1))
const pageEnd = computed(() => Math.min(currentPage.value * pageSize, total.value))
const visiblePages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  for (let page = start; page <= end; page += 1) pages.push(page)
  return pages
})

const pokemonSearchKeyword = ref<Record<number, string>>({})
const pokemonSearchResults = ref<Record<number, OpsPokemonLineupSearchItem[]>>({})
const pokemonSearchVisible = ref<Record<number, boolean>>({})
const skillSearchKeyword = ref<Record<string, string>>({})
const skillSearchResults = ref<Record<string, OpsPokemonLineupSearchItem[]>>({})
const skillSearchVisible = ref<Record<string, boolean>>({})

let pokemonSearchTimer: ReturnType<typeof setTimeout> | undefined
let skillSearchTimer: ReturnType<typeof setTimeout> | undefined

function emptyMember(sortOrder: number): MemberForm {
  return {
    pokemon_id: null,
    random_pk_dict_id: null,
    pokemon_name: '',
    pokemon_image: '',
    sort_order: sortOrder,
    bloodline_dict_id: null,
    personality_id: null,
    qual_1: '',
    qual_2: '',
    qual_3: '',
    skills: [
      { id: null, name: '', image: '' },
      { id: null, name: '', image: '' },
      { id: null, name: '', image: '' },
      { id: null, name: '', image: '' },
    ],
    member_desc: '',
  }
}

function sourceTypeLabel(value: string): string {
  return lineupTypeOptions.value.find((item) => item.code === value)?.label || value || '未分类'
}

function skillKey(memberIndex: number, skillIndex: number): string {
  return `${memberIndex}-${skillIndex}`
}

function normalizeAttrToken(s: string): string {
  return s.replace(/系$/u, '').trim()
}

function attrImageUrlForBloodlineLabel(label: string): string {
  const attrs = attributes.value
  if (!label || !attrs.length) return ''
  const lb = label.trim()
  const lbNorm = normalizeAttrToken(lb)
  for (const a of attrs) {
    const name = a.attr_name.trim()
    const nameNorm = normalizeAttrToken(name)
    if (name === lb || nameNorm === lbNorm || lb.includes(name) || name.includes(lbNorm)) {
      return a.attr_image || ''
    }
  }
  return ''
}

function randomPkModesForInput(kwRaw: string): BattlePkRandomPokemonOption[] {
  const modes = randomPokemonModes.value
  const kw = kwRaw.trim()
  if (!kw) return modes
  return modes.filter((o) => o.label.includes(kw))
}

function randomPkLabel(member: MemberForm): string {
  if (member.random_pk_dict_id === null) return ''
  return randomPokemonModes.value.find((o) => o.id === member.random_pk_dict_id)?.label ?? ''
}

function pickRandomPkOption(memberIndex: number, opt: BattlePkRandomPokemonOption) {
  const member = form.members[memberIndex]
  if (!member) return
  member.random_pk_dict_id = opt.id
  member.pokemon_id = null
  member.pokemon_name = opt.label
  member.pokemon_image = ''
  member.personality_id = null
  member.qual_1 = ''
  member.qual_2 = ''
  member.qual_3 = ''
  member.skills = [
    { id: null, name: '', image: '' },
    { id: null, name: '', image: '' },
    { id: null, name: '', image: '' },
    { id: null, name: '', image: '' },
  ]
  if (opt.kind === 'any') {
    member.bloodline_dict_id = null
  } else if (opt.kind === 'attr' && opt.bloodline_code) {
    const bl = bloodlineOptions.value.find((x) => x.code === opt.bloodline_code)
    if (bl) {
      member.bloodline_dict_id = bl.id
      member.pokemon_image = attrImageUrlForBloodlineLabel(bl.label)
    }
  }
  pokemonSearchKeyword.value[memberIndex] = ''
  pokemonSearchVisible.value[memberIndex] = false
}

function statLabel(code: string | null | undefined): string {
  if (!code) return ''
  const hit = statOptions.value.find((s) => s.value === code)
  return hit?.label || code
}

function personalitySelectLabel(p: OpsPersonalityItem): string {
  const base = (p.name || '').trim() || `性格#${p.id}`
  if (p.is_neutral || (!p.buff_stat && !p.nerf_stat)) {
    return `${base}（平衡）`
  }
  const b = p.buff_stat ? statLabel(p.buff_stat) : ''
  const n = p.nerf_stat ? statLabel(p.nerf_stat) : ''
  const parts: string[] = []
  if (b) parts.push(`+${b}`)
  if (n) parts.push(`-${n}`)
  if (!parts.length) return base
  return `${base}（${parts.join(' ')}）`
}

function personalityOptionTitle(p: OpsPersonalityItem): string {
  const line = personalitySelectLabel(p)
  if (p.is_neutral || (!p.buff_stat && !p.nerf_stat)) {
    return `${line}，全项无百分比修正`
  }
  const fmtPct = (key: OpsPersonalityStat) => {
    const raw = Number(p[PERSONALITY_MOD_COL[key]] ?? 0)
    if (!raw) return ''
    const pct = Math.round(raw * 100)
    return `${statLabel(key)} ${pct > 0 ? '+' : ''}${pct}%`
  }
  const bits: string[] = []
  if (p.buff_stat) {
    const s = fmtPct(p.buff_stat)
    if (s) bits.push(s)
  }
  if (p.nerf_stat) {
    const s = fmtPct(p.nerf_stat)
    if (s) bits.push(s)
  }
  return bits.length ? `${line}｜${bits.join('，')}` : line
}

async function loadOptions() {
  const results = await Promise.allSettled([
    fetchOpsDicts({ dict_type: BLOODLINE_DICT_TYPE, page: 1, page_size: 100 }),
    fetchOpsPersonalities({ page: 1, page_size: 100 }),
    fetchOpsDicts({ dict_type: STAT_DICT_TYPE, page: 1, page_size: 100 }),
    fetchOpsDicts({ dict_type: LINEUP_TYPE_DICT, page: 1, page_size: 100 }),
    fetchOpsResonanceMagics({ page: 1, page_size: 200 }),
    fetchAttributes(),
    fetchBattlePkRandomPokemonModes(),
  ])

  if (results[0].status === 'fulfilled') bloodlineOptions.value = results[0].value.items
  if (results[1].status === 'fulfilled') personalityOptions.value = results[1].value.items
  if (results[3].status === 'fulfilled') lineupTypeOptions.value = results[3].value.items
  if (results[4].status === 'fulfilled') resonanceMagicOptions.value = results[4].value.items
  if (results[5].status === 'fulfilled') attributes.value = results[5].value
  if (results[6].status === 'fulfilled') randomPokemonModes.value = results[6].value

  if (results[2].status === 'fulfilled') {
    statOptions.value = results[2].value.items.map((item) => ({
      value: item.code as OpsPokemonLineupStatKey,
      label: item.label || item.code,
    }))
  }
}

function resetForm() {
  editingId.value = null
  form.title = ''
  form.lineup_desc = ''
  form.source_type = ''
  form.resonance_magic_id = null
  form.sort_order = 1
  form.is_active = true
  form.members = [emptyMember(1)]
  pokemonSearchKeyword.value = {}
  pokemonSearchResults.value = {}
  pokemonSearchVisible.value = {}
  skillSearchKeyword.value = {}
  skillSearchResults.value = {}
  skillSearchVisible.value = {}
}

function openCreateDrawer() {
  resetForm()
  drawerVisible.value = true
}

function closeDrawer() {
  drawerVisible.value = false
}

async function editItem(item: OpsPokemonLineupListItem) {
  try {
    loading.value = true
    const detail = await fetchOpsPokemonLineup(item.id)
    editingId.value = detail.id
    form.title = detail.title
    form.lineup_desc = detail.lineup_desc
    form.resonance_magic_id = detail.resonance_magic_id
    form.sort_order = detail.sort_order || 1
    form.is_active = detail.is_active
    form.members = detail.members.length > 0
      ? detail.members.map((m, i) => ({
          pokemon_id: m.pokemon_id,
          random_pk_dict_id: m.random_pk_dict_id ?? null,
          pokemon_name: m.pokemon_name,
          pokemon_image: m.pokemon_image,
          sort_order: i + 1,
          bloodline_dict_id: m.bloodline_dict_id,
          personality_id: m.personality_id,
          qual_1: m.qual_1,
          qual_2: m.qual_2,
          qual_3: m.qual_3,
          skills: [
            { id: m.skill_1_id, name: m.skill_1_name, image: m.skill_1_image || '' },
            { id: m.skill_2_id, name: m.skill_2_name, image: m.skill_2_image || '' },
            { id: m.skill_3_id, name: m.skill_3_name, image: m.skill_3_image || '' },
            { id: m.skill_4_id, name: m.skill_4_name, image: m.skill_4_image || '' },
          ],
          member_desc: m.member_desc,
        }))
      : [emptyMember(1)]
    // 必须在 members 赋值之后再写 source_type，否则依赖分类的槽位逻辑会读到旧 members
    form.source_type = detail.source_type || ''
    await nextTick()
    ensureShiningContestMemberSlots()
    drawerVisible.value = true
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '加载详情失败', 'error')
  } finally {
    loading.value = false
  }
}

function ensureShiningContestMemberSlots() {
  if (!requiresSixSlotsLineup.value) return
  while (form.members.length < 6) {
    form.members.push(emptyMember(form.members.length + 1))
  }
  if (form.members.length > 6) {
    form.members.splice(6)
  }
  form.members.forEach((member, idx) => { member.sort_order = idx + 1 })
}

async function onLineupSourceTypeChange() {
  // 与 v-model 同一 tick 内先触发 change，需等 DOM/模型更新后再读 form.source_type
  await nextTick()
  ensureShiningContestMemberSlots()
}

function addMember() {
  if (requiresSixSlotsLineup.value) return
  if (form.members.length >= 6) return
  form.members.push(emptyMember(form.members.length + 1))
}

function removeMember(index: number) {
  if (requiresSixSlotsLineup.value) return
  form.members.splice(index, 1)
  form.members.forEach((member, idx) => { member.sort_order = idx + 1 })
}

function onPokemonSearchInput(memberIndex: number) {
  if (pokemonSearchTimer) clearTimeout(pokemonSearchTimer)
  pokemonSearchTimer = setTimeout(async () => {
    const kw = (pokemonSearchKeyword.value[memberIndex] || '').trim()
    if (!kw) {
      pokemonSearchResults.value[memberIndex] = []
      pokemonSearchVisible.value[memberIndex] = randomPkModesForInput('').length > 0
      return
    }
    try {
      const res = await searchPokemonLineupPokemon(kw)
      pokemonSearchResults.value[memberIndex] = res.items
      pokemonSearchVisible.value[memberIndex] = true
    } catch { /* ignore */ }
  }, 300)
}

function openPokemonDropdown(memberIndex: number) {
  const kw = (pokemonSearchKeyword.value[memberIndex] || '').trim()
  if (!kw) {
    pokemonSearchResults.value[memberIndex] = []
    pokemonSearchVisible.value[memberIndex] = randomPkModesForInput('').length > 0
    return
  }
  onPokemonSearchInput(memberIndex)
}

function selectPokemon(memberIndex: number, item: OpsPokemonLineupSearchItem) {
  const member = form.members[memberIndex]
  if (!member) return
  member.pokemon_id = item.id
  member.random_pk_dict_id = null
  member.pokemon_name = item.name
  member.pokemon_image = item.image || ''
  pokemonSearchKeyword.value[memberIndex] = ''
  pokemonSearchVisible.value[memberIndex] = false
}

function clearPokemon(memberIndex: number) {
  const member = form.members[memberIndex]
  if (!member) return
  member.pokemon_id = null
  member.random_pk_dict_id = null
  member.pokemon_name = ''
  member.pokemon_image = ''
  member.skills = member.skills.map(() => ({ id: null, name: '', image: '' }))
  for (let i = 0; i < 4; i += 1) {
    const key = skillKey(memberIndex, i)
    skillSearchKeyword.value[key] = ''
    skillSearchResults.value[key] = []
    skillSearchVisible.value[key] = false
  }
}

function onSkillSearchInput(memberIndex: number, skillIndex: number) {
  const member = form.members[memberIndex]
  const key = skillKey(memberIndex, skillIndex)
  if (!member || !member.pokemon_id) {
    skillSearchResults.value[key] = []
    skillSearchVisible.value[key] = false
    return
  }
  if (skillSearchTimer) clearTimeout(skillSearchTimer)
  skillSearchTimer = setTimeout(async () => {
    const kw = (skillSearchKeyword.value[key] || '').trim()
    const excludeIds = member.skills
      .map((skill, idx) => (idx === skillIndex ? null : skill.id))
      .filter((id): id is number => !!id)
    try {
      const res = await searchPokemonLineupSkills({
        keyword: kw,
        pokemon_id: member.pokemon_id!,
        exclude_skill_ids: excludeIds,
      })
      skillSearchResults.value[key] = res.items
      skillSearchVisible.value[key] = true
    } catch { /* ignore */ }
  }, 300)
}

function selectSkill(memberIndex: number, skillIndex: number, item: OpsPokemonLineupSearchItem) {
  const member = form.members[memberIndex]
  if (!member) return
  member.skills[skillIndex] = { id: item.id, name: item.name, image: item.image || '' }
  const key = skillKey(memberIndex, skillIndex)
  skillSearchKeyword.value[key] = ''
  skillSearchVisible.value[key] = false
}

function clearSkill(memberIndex: number, skillIndex: number) {
  const member = form.members[memberIndex]
  if (!member) return
  member.skills[skillIndex] = { id: null, name: '', image: '' }
}

function hidePokemonSearch(memberIndex: number) {
  window.setTimeout(() => { pokemonSearchVisible.value[memberIndex] = false }, 200)
}

function hideSkillSearch(memberIndex: number, skillIndex: number) {
  const key = skillKey(memberIndex, skillIndex)
  window.setTimeout(() => { skillSearchVisible.value[key] = false }, 200)
}

function validateMember(member: MemberForm, index: number): string {
  const hasPokemon = member.pokemon_id != null
  const hasRandom = member.random_pk_dict_id != null
  if (!hasPokemon && !hasRandom) return `第 ${index + 1} 只精灵未选择`
  if (hasPokemon && hasRandom) return `第 ${index + 1} 只不能同时选择具体精灵与随机精灵`
  const stats = [member.qual_1, member.qual_2, member.qual_3].filter(Boolean)
  if (new Set(stats).size !== stats.length) return `第 ${index + 1} 只精灵资质属性不能重复`
  const skillIds = member.skills.map((skill) => skill.id).filter(Boolean)
  if (hasRandom && skillIds.length) return `第 ${index + 1} 只随机精灵不能配置技能`
  if (new Set(skillIds).size !== skillIds.length) return `第 ${index + 1} 只精灵技能不能重复`
  return ''
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [me, data] = await Promise.all([
      fetchOpsMe(),
      fetchOpsPokemonLineups({
        keyword: keyword.value.trim(),
        source_type: sourceTypeFilter.value.trim(),
        is_active: isActiveFilter.value === '' ? null : isActiveFilter.value === 'true',
        page: currentPage.value,
        page_size: pageSize,
      }),
    ])
    isAdmin.value = me.role === 'admin'
    items.value = data.items
    total.value = data.total
    currentPage.value = data.page
  } catch (err: any) {
    const detail = err?.response?.data?.detail || '加载失败'
    if (err?.response?.status === 401) { clearOpsToken(); return }
    error.value = detail
  } finally {
    loading.value = false
  }
}

async function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  await loadData()
}

async function search() {
  currentPage.value = 1
  await loadData()
}

async function resetFilters() {
  keyword.value = ''
  sourceTypeFilter.value = ''
  isActiveFilter.value = ''
  currentPage.value = 1
  await loadData()
}

async function submitForm() {
  if (saving.value) return
  if (!form.title.trim()) {
    showOpsToast('阵容标题不能为空', 'error')
    return
  }
  if (!form.members.length) {
    showOpsToast('至少需要配置 1 只精灵', 'error')
    return
  }
  if (requiresSixSlotsLineup.value && form.members.length !== 6) {
    showOpsToast('闪耀大赛阵容必须包含 6 只精灵', 'error')
    return
  }
  for (const [index, member] of form.members.entries()) {
    const message = validateMember(member, index)
    if (message) {
      showOpsToast(message, 'error')
      return
    }
  }

  saving.value = true
  error.value = ''
  try {
    const payload = {
      title: form.title.trim(),
      lineup_desc: form.lineup_desc,
      source_type: String(form.source_type ?? '').trim(),
      resonance_magic_id: form.resonance_magic_id,
      sort_order: Number(form.sort_order || 1),
      is_active: form.is_active,
      members: form.members.map((member, index) => ({
        pokemon_id: member.pokemon_id,
        random_pk_dict_id: member.random_pk_dict_id,
        sort_order: index + 1,
        bloodline_dict_id: member.bloodline_dict_id || null,
        personality_id: member.personality_id || null,
        qual_1: member.qual_1,
        qual_2: member.qual_2,
        qual_3: member.qual_3,
        skill_1_id: member.skills[0]?.id || null,
        skill_2_id: member.skills[1]?.id || null,
        skill_3_id: member.skills[2]?.id || null,
        skill_4_id: member.skills[3]?.id || null,
        member_desc: member.member_desc,
      })),
    }
    if (editingId.value) {
      await updateOpsPokemonLineup(editingId.value, payload)
      showOpsToast('精灵阵容已更新', 'success')
    } else {
      await createOpsPokemonLineup(payload)
      showOpsToast('精灵阵容已创建', 'success')
    }
    resetForm()
    closeDrawer()
    await loadData()
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '保存失败'
    showOpsToast(error.value, 'error')
  } finally {
    saving.value = false
  }
}

async function removeItem(item: OpsPokemonLineupListItem) {
  if (!isAdmin.value) return
  if (!window.confirm(`确定删除阵容「${item.title}」吗？`)) return
  try {
    await deleteOpsPokemonLineup(item.id)
    if (editingId.value === item.id) resetForm()
    await loadData()
    showOpsToast('精灵阵容已删除', 'success')
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '删除失败'
    showOpsToast(error.value, 'error')
  }
}

onMounted(async () => {
  resetForm()
  await Promise.all([loadOptions(), loadData()])
})
</script>

<template>
  <div class="ops-page">
    <section class="ops-card-padded">
      <div class="ops-filter-bar" style="align-items:flex-end;flex-wrap:wrap;">
        <label class="ops-form-item" style="min-width:200px;">
          <span class="ops-filter-label">阵容标题</span>
          <input v-model="keyword" class="ops-input" type="text" placeholder="请输入阵容标题" @keyup.enter="search" />
        </label>
        <label class="ops-form-item" style="min-width:160px;">
          <span class="ops-filter-label">分类</span>
          <select v-model="sourceTypeFilter" class="ops-select">
            <option value="">全部</option>
            <option v-for="opt in lineupTypeOptions" :key="opt.id" :value="opt.code">{{ opt.label }}</option>
          </select>
        </label>
        <label class="ops-form-item" style="min-width:160px;">
          <span class="ops-filter-label">状态</span>
          <select v-model="isActiveFilter" class="ops-select">
            <option value="">全部</option>
            <option value="true">启用</option>
            <option value="false">禁用</option>
          </select>
        </label>
        <div class="ops-filter-actions">
          <button type="button" class="ops-btn ops-btn-primary" @click="search">搜索</button>
          <button type="button" class="ops-btn ops-btn-secondary" @click="resetFilters">重置</button>
        </div>
      </div>
    </section>

    <section class="ops-card-padded">
      <div class="ops-toolbar">
        <button type="button" class="ops-btn ops-btn-primary" @click="openCreateDrawer">新增</button>
        <span class="ops-toolbar-meta">共 {{ total }} 条</span>
      </div>

      <p v-if="error" class="ops-error">{{ error }}</p>

      <div v-if="loading" class="ops-loading">加载中...</div>
      <div v-else-if="!items.length" class="ops-empty">
        <strong>暂无数据</strong>
        <span>请调整查询条件后重试，或新增阵容。</span>
      </div>
      <div v-else class="ops-table-wrap">
        <table class="ops-table">
          <thead>
            <tr>
              <th class="ops-col-index">序号</th>
              <th>标题</th>
              <th>分类</th>
              <th>共鸣魔法</th>
              <th>成员数</th>
              <th class="ops-col-sort">排序</th>
              <th>状态</th>
              <th class="ops-col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td style="font-weight:500;color:var(--ops-text);">{{ item.title || '-' }}</td>
              <td>{{ sourceTypeLabel(item.source_type) }}</td>
              <td>{{ item.resonance_magic_name || '-' }}</td>
              <td>{{ item.member_count }}</td>
              <td>{{ item.sort_order }}</td>
              <td>
                <span class="ops-badge" :class="item.is_active ? 'ops-badge--success' : 'ops-badge--default'">
                  {{ item.is_active ? '启用' : '禁用' }}
                </span>
              </td>
              <td>
                <div class="ops-action-group">
                  <button type="button" class="ops-btn ops-btn-text" @click="editItem(item)">修改</button>
                  <button v-if="isAdmin" type="button" class="ops-btn ops-btn-text ops-btn--danger" @click="removeItem(item)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="total > 0" class="ops-pagination">
        <span class="ops-pagination-summary">共 {{ total }} 条，当前显示 {{ pageStart }}-{{ pageEnd }} 条</span>
        <div class="ops-pagination-controls">
          <button type="button" class="ops-page-btn" :disabled="currentPage === 1" @click="goToPage(1)">首页</button>
          <button type="button" class="ops-page-btn" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">上一页</button>
          <button
            v-for="page in visiblePages"
            :key="page"
            type="button"
            class="ops-page-btn"
            :class="{ 'ops-page-btn--active': page === currentPage }"
            @click="goToPage(page)"
          >{{ page }}</button>
          <button type="button" class="ops-page-btn" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">下一页</button>
          <button type="button" class="ops-page-btn" :disabled="currentPage === totalPages" @click="goToPage(totalPages)">末页</button>
        </div>
      </div>
    </section>

    <div v-if="drawerVisible" class="ops-modal-mask">
      <section class="ops-modal" @click.stop>
        <div class="ops-modal-header">
          <h3>{{ editingId ? '编辑精灵阵容' : '新增精灵阵容' }}</h3>
          <button type="button" class="ops-modal-close" @click="closeDrawer">✕</button>
        </div>

        <form class="ops-modal-body" @submit.prevent="submitForm">
          <div
            style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px 20px;"
          >
            <label class="ops-form-item" style="gap:6px;">
              <span>标题</span>
              <input v-model="form.title" class="ops-input" required type="text" maxlength="50" placeholder="请输入阵容标题" />
            </label>
            <label class="ops-form-item" style="gap:6px;">
              <span>分类</span>
              <select v-model="form.source_type" class="ops-select" @change="onLineupSourceTypeChange">
                <option value="">未设置</option>
                <option v-for="opt in lineupTypeOptions" :key="opt.id" :value="opt.code">{{ opt.label }}</option>
              </select>
            </label>
            <label class="ops-form-item" style="gap:6px;">
              <span>排序</span>
              <input v-model.number="form.sort_order" class="ops-input" type="number" min="1" placeholder="默认 1" />
            </label>
            <label class="ops-form-item" style="gap:6px;">
              <span>共鸣</span>
              <select v-model="form.resonance_magic_id" class="ops-select">
                <option :value="null">未设置</option>
                <option v-for="opt in resonanceMagicOptions" :key="opt.id" :value="opt.id">{{ opt.name }}</option>
              </select>
            </label>
            <label class="ops-form-item" style="gap:6px;">
              <span>状态</span>
              <select v-model="form.is_active" class="ops-select">
                <option :value="true">启用</option>
                <option :value="false">禁用</option>
              </select>
            </label>
          </div>

          <div
            style="display:flex;align-items:center;justify-content:space-between;margin-top:24px;margin-bottom:12px;"
          >
            <span style="font-size:14px;font-weight:600;color:var(--ops-text);">阵容成员</span>
            <span v-if="requiresSixSlotsLineup" style="flex:1;margin-left:12px;font-size:12px;font-weight:normal;color:var(--ops-muted);">闪耀大赛须固定 6 只精灵</span>
            <button
              v-if="!requiresSixSlotsLineup && form.members.length < 6"
              type="button"
              class="ops-btn ops-btn-sm ops-btn-primary"
              @click="addMember"
            >+ 添加精灵</button>
          </div>

          <div
            v-for="(member, mi) in form.members"
            :key="mi"
            style="border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);padding:14px 16px;margin-bottom:12px;background:var(--ops-bg);"
          >
            <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px;">
              <div style="display:flex;align-items:center;gap:10px;">
                <div style="width:40px;height:40px;border-radius:4px;background:var(--ops-surface);border:1px solid var(--ops-border);display:grid;place-items:center;overflow:hidden;font-size:12px;color:var(--ops-muted);">
                  <img v-if="member.pokemon_image" :src="member.pokemon_image" style="width:100%;height:100%;object-fit:contain;" alt="" />
                  <span v-else>#{{ mi + 1 }}</span>
                </div>
                <div style="display:grid;gap:2px;">
                  <strong style="font-size:14px;color:var(--ops-text);">{{ member.pokemon_name || randomPkLabel(member) || `精灵 ${mi + 1}` }}</strong>
                  <small style="font-size:12px;color:var(--ops-muted);">第 {{ mi + 1 }} 只</small>
                </div>
              </div>
              <button
                v-if="!requiresSixSlotsLineup && form.members.length > 1"
                type="button"
                class="ops-btn ops-btn-text ops-btn--danger"
                @click="removeMember(mi)"
              >移除</button>
            </div>

            <div
              style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px 20px;margin-top:12px;"
            >
              <div class="ops-form-row" style="position:relative;grid-template-columns:1fr;gap:6px;">
                <span>精灵</span>
                <div v-if="member.pokemon_id || member.random_pk_dict_id !== null" style="display:inline-flex;align-items:center;gap:8px;padding:4px 10px;background:var(--ops-accent-light);border:1px solid color-mix(in srgb, var(--ops-accent) 30%, transparent);border-radius:4px;font-size:13px;color:var(--ops-accent);max-width:100%;">
                  <img v-if="member.pokemon_image" :src="member.pokemon_image" style="width:24px;height:24px;border-radius:4px;object-fit:contain;background:var(--ops-surface);" alt="" />
                  <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ member.pokemon_name || randomPkLabel(member) }}</span>
                  <button type="button" style="border:none;background:transparent;color:var(--ops-muted);cursor:pointer;font-size:16px;line-height:1;padding:0 2px;" @click="clearPokemon(mi)">&times;</button>
                </div>
                <div v-else style="position:relative;">
                  <input
                    v-model="pokemonSearchKeyword[mi]"
                    class="ops-input"
                    type="text"
                    placeholder="搜索精灵或选择随机项..."
                    style="width:100%;height:32px;"
                    @keydown.enter.prevent
                    @input="onPokemonSearchInput(mi)"
                    @focus="openPokemonDropdown(mi)"
                    @blur="hidePokemonSearch(mi)"
                  />
                  <div
                    v-if="pokemonSearchVisible[mi]"
                    style="position:absolute;top:100%;left:0;right:0;background:var(--ops-surface);border:1px solid var(--ops-border);border-radius:var(--ops-radius-sm);box-shadow:0 4px 12px rgba(0,0,0,0.1);max-height:220px;overflow:auto;z-index:10;"
                  >
                    <div
                      v-for="opt in randomPkModesForInput(pokemonSearchKeyword[mi] || '')"
                      :key="`rand-${opt.id}`"
                      style="display:flex;align-items:center;gap:8px;padding:8px 12px;cursor:pointer;font-size:13px;color:#e6a23c;"
                      @mousedown.prevent="pickRandomPkOption(mi, opt)"
                    >
                      <span>{{ opt.label }}</span>
                    </div>
                    <template v-if="(pokemonSearchKeyword[mi] || '').trim()">
                      <div
                        v-for="opt in pokemonSearchResults[mi]"
                        :key="opt.id"
                        class="ops-dd-hover"
                        style="display:flex;align-items:center;gap:8px;padding:8px 12px;cursor:pointer;font-size:13px;color:var(--ops-text);"
                        @mousedown.prevent="selectPokemon(mi, opt)"
                      >
                        <img v-if="opt.image" :src="opt.image" style="width:28px;height:28px;border-radius:4px;object-fit:contain;background:var(--ops-surface);" alt="" />
                        <span>{{ opt.name }}</span>
                      </div>
                    </template>
                    <div
                      v-if="
                        !randomPkModesForInput(pokemonSearchKeyword[mi] || '').length
                          && (!(pokemonSearchKeyword[mi] || '').trim()
                            || !(pokemonSearchResults[mi]?.length))
                      "
                      style="display:flex;align-items:center;gap:8px;padding:8px 12px;cursor:default;font-size:12px;color:var(--ops-muted);"
                    >
                      {{
                        !(pokemonSearchKeyword[mi] || '').trim()
                          ? '暂无随机选项（请先在后端 seed 字典）'
                          : '没有匹配的精灵或随机项'
                      }}
                    </div>
                  </div>
                </div>
              </div>
              <label class="ops-form-row" style="grid-template-columns:1fr;gap:6px;">
                <span>血脉</span>
                <select v-model="member.bloodline_dict_id" class="ops-select">
                  <option :value="null">未设置</option>
                  <option v-for="opt in bloodlineOptions" :key="opt.id" :value="opt.id">{{ opt.label }}</option>
                </select>
              </label>
              <label class="ops-form-row" style="grid-template-columns:1fr;gap:6px;">
                <span>性格</span>
                <select v-model="member.personality_id" class="ops-select">
                  <option :value="null">未设置</option>
                  <option
                    v-for="opt in personalityOptions"
                    :key="opt.id"
                    :value="opt.id"
                    :title="personalityOptionTitle(opt)"
                  >
                    {{ personalitySelectLabel(opt) }}
                  </option>
                </select>
              </label>
            </div>

            <div style="margin:14px 0 8px;font-size:13px;font-weight:600;color:var(--ops-text-secondary);">三项资质</div>
            <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;">
              <select v-model="member.qual_1" class="ops-select">
                <option value="">未设置</option>
                <option v-for="opt in statOptions" :key="`q1-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
              </select>
              <select v-model="member.qual_2" class="ops-select">
                <option value="">未设置</option>
                <option v-for="opt in statOptions" :key="`q2-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
              </select>
              <select v-model="member.qual_3" class="ops-select">
                <option value="">未设置</option>
                <option v-for="opt in statOptions" :key="`q3-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>

            <div style="margin:14px 0 8px;font-size:13px;font-weight:600;color:var(--ops-text-secondary);">技能配置</div>
            <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;">
              <div v-for="si in 4" :key="si" class="ops-form-row" style="position:relative;grid-template-columns:1fr;gap:6px;margin-bottom:0;">
                <span>技能{{ si }}</span>
                <div v-if="member.skills[si - 1]?.id" style="display:inline-flex;align-items:center;gap:8px;padding:4px 10px;background:var(--ops-accent-light);border:1px solid color-mix(in srgb, var(--ops-accent) 30%, transparent);border-radius:4px;font-size:13px;color:var(--ops-accent);max-width:100%;">
                  <img v-if="member.skills[si - 1]?.image" :src="member.skills[si - 1]?.image" style="width:24px;height:24px;border-radius:4px;object-fit:contain;background:var(--ops-surface);" alt="" />
                  <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ member.skills[si - 1]!.name }}</span>
                  <button type="button" style="border:none;background:transparent;color:var(--ops-muted);cursor:pointer;font-size:16px;line-height:1;padding:0 2px;" @click="clearSkill(mi, si - 1)">&times;</button>
                </div>
                <div v-else style="position:relative;">
                  <input
                    v-model="skillSearchKeyword[skillKey(mi, si - 1)]"
                    class="ops-input"
                    type="text"
                    :placeholder="member.pokemon_id ? '搜索技能...' : '请先选择精灵'"
                    :disabled="!member.pokemon_id"
                    style="width:100%;height:32px;"
                    @keydown.enter.prevent
                    @input="onSkillSearchInput(mi, si - 1)"
                    @focus="onSkillSearchInput(mi, si - 1)"
                    @blur="hideSkillSearch(mi, si - 1)"
                  />
                  <div
                    v-if="skillSearchVisible[skillKey(mi, si - 1)] && skillSearchResults[skillKey(mi, si - 1)]?.length"
                    style="position:absolute;top:100%;left:0;right:0;background:var(--ops-surface);border:1px solid var(--ops-border);border-radius:var(--ops-radius-sm);box-shadow:0 4px 12px rgba(0,0,0,0.1);max-height:220px;overflow:auto;z-index:10;"
                  >
                    <div
                      v-for="opt in skillSearchResults[skillKey(mi, si - 1)]"
                      :key="opt.id"
                      class="ops-dd-hover"
                      style="display:flex;align-items:center;gap:8px;padding:8px 12px;cursor:pointer;font-size:13px;color:var(--ops-text);"
                      @mousedown.prevent="selectSkill(mi, si - 1, opt)"
                    >
                      <img v-if="opt.image" :src="opt.image" style="width:28px;height:28px;border-radius:4px;object-fit:contain;background:var(--ops-surface);" alt="" />
                      <span>{{ opt.name }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div style="margin:14px 0 8px;font-size:13px;font-weight:600;color:var(--ops-text-secondary);">成员说明</div>
            <textarea
              v-model="member.member_desc"
              class="ops-input"
              rows="3"
              style="width:100%;height:auto;min-height:72px;padding:10px 14px;resize:vertical;"
              placeholder="请输入该精灵的补充说明..."
            ></textarea>
          </div>

          <div
            style="display:flex;align-items:center;justify-content:space-between;margin-top:24px;margin-bottom:8px;"
          >
            <span style="font-size:14px;font-weight:600;color:var(--ops-text);">阵容说明</span>
          </div>
          <textarea
            v-model="form.lineup_desc"
            class="ops-input"
            rows="5"
            style="width:100%;height:auto;min-height:100px;padding:10px 14px;resize:vertical;"
            placeholder="请输入整体阵容说明..."
          ></textarea>

          <div class="ops-modal-footer" style="justify-content:center;margin-top:20px;">
            <button type="button" class="ops-btn ops-btn-primary" :disabled="saving" @click="submitForm">{{ saving ? '保存中...' : '保存' }}</button>
            <button type="button" class="ops-btn ops-btn-secondary" @click="closeDrawer">取消</button>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>

<style scoped>
.ops-dd-hover:hover { background: var(--ops-bg); }
</style>
