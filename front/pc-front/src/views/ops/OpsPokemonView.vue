<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  clearOpsToken,
  createOpsPokemon,
  deleteOpsPokemon,
  fetchOpsDicts,
  fetchOpsMe,
  fetchOpsPokemon,
  fetchOpsPokemonDetail,
  fetchOpsPokemonEvolutionChain,
  fetchOpsPokemonOptions,
  searchOpsPokemonEvolutionChain,
  showOpsToast,
  syncOpsPokemonLkgcSkills,
  updateOpsPokemonEvolutionChain,
  updateOpsPokemon,
  uploadOpsFriendImage,
  uploadOpsYiseImage,
  type OpsEvolutionChainStep,
  type OpsPokemonLkgcSkillSyncResponse,
  type OpsPokemonDetail,
  type OpsPokemonItem,
  type OpsPokemonOptionItem,
  type OpsPokemonSkillItem,
} from '@/api/ops'

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const filterNo = ref('')
const filterName = ref('')
const filterAttrId = ref<number | ''>('')
const filterEggGroup = ref('')
const filterTypeCode = ref('')
const filterFormCode = ref('')
const filterTraitId = ref<number | ''>('')
const filterTraitKeyword = ref('')
const traitSuggestVisible = ref(false)
const items = ref<OpsPokemonItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const isAdmin = ref(false)
const totalPages = ref(1)

const modalVisible = ref(false)
const editingId = ref<number | null>(null)
const syncSkillModalVisible = ref(false)
const syncingSkills = ref(false)
const syncSkillTarget = ref<OpsPokemonItem | null>(null)
const syncSkillResult = ref<OpsPokemonLkgcSkillSyncResponse | null>(null)
const syncSkillError = ref('')

const traits = ref<OpsPokemonOptionItem[]>([])
const attributes = ref<OpsPokemonOptionItem[]>([])
const skills = ref<OpsPokemonOptionItem[]>([])
const eggGroupOptions = ref<string[]>([])
const typeOptions = ref<Array<{ code: string; label: string }>>([])
const formOptions = ref<Array<{ code: string; label: string }>>([])
const skillSourceOptions = ref<Array<{ code: string; label: string }>>([])

const skillPage = ref(1)
const skillPageSize = 8
const skillKeyword = ref('')
const skillSelectorVisible = ref(false)
const skillSelectorKeyword = ref('')
const skillSelectorPage = ref(1)
const skillSelectorPageSize = 8
const evolutionSteps = ref<OpsEvolutionChainStep[]>([])
const evolutionChainId = ref<number | null>(null)
const evolutionSearchKeyword = ref('')
const evolutionPokemonKeyword = ref('')
const evolutionPokemonCandidates = ref<OpsPokemonItem[]>([])
const evolutionPokemonSearching = ref(false)
/** 已选但未保存的图片（保存时再上传） */
const pendingFriendFile = ref<File | null>(null)
const pendingFriendPreviewUrl = ref('')
const friendFileInputRef = ref<HTMLInputElement | null>(null)
/** 异色立绘 */
const pendingYiseFile = ref<File | null>(null)
const pendingYisePreviewUrl = ref('')
const yiseFileInputRef = ref<HTMLInputElement | null>(null)
const evolutionEditorVisible = ref(false)
const evolutionEditingIndex = ref<number | null>(null)
const evolutionDraft = reactive<OpsEvolutionChainStep>({
  sort_order: 1,
  pokemon_name: '',
  evolution_condition: '',
  pre_evolution_condition: '',
  image_url: '',
  matched: false,
})

function pageStart() {
  if (total.value === 0) return 0
  return (page.value - 1) * pageSize + 1
}

function pageEnd() {
  return Math.min(page.value * pageSize, total.value)
}

function visiblePages() {
  const pages: number[] = []
  const start = Math.max(1, page.value - 2)
  const end = Math.min(totalPages.value, page.value + 2)
  for (let p = start; p <= end; p += 1) {
    pages.push(p)
  }
  return pages
}

async function goToPage(target: number) {
  if (target < 1 || target > totalPages.value || target === page.value) return
  page.value = target
  await loadList()
}

const form = reactive<OpsPokemonDetail>({
  id: 0,
  no: '',
  name: '',
  image: '',
  type: '',
  type_name: '',
  form: '',
  form_name: '',
  egg_group: '',
  trait_id: 0,
  detail_url: '',
  image_lc: '',
  image_yise: '',
  chain_id: null,
  hp: 0,
  atk: 0,
  matk: 0,
  def_val: 0,
  mdef: 0,
  spd: 0,
  total_race: 0,
  obtain_method: '',
  attribute_ids: [],
  egg_groups: [],
  skills: [],
})

const friendStaticBase = (import.meta.env.VITE_STATIC_BASE_URL || 'https://wikiroco.com').replace(/\/+$/, '')

const friendDisplaySrc = computed(() => {
  if (pendingFriendPreviewUrl.value) return pendingFriendPreviewUrl.value
  const lc = (form.image_lc || '').trim()
  if (!lc) return ''
  if (lc.startsWith('http')) return lc
  return `${friendStaticBase}/images/friends/${lc.replace(/^\//, '')}`
})

const yiseDisplaySrc = computed(() => {
  if (pendingYisePreviewUrl.value) return pendingYisePreviewUrl.value
  const yise = (form.image_yise || '').trim()
  if (!yise) return ''
  if (yise.startsWith('http')) return yise
  return `${friendStaticBase}/images${yise}`
})

function revokeFriendPendingPreview() {
  if (pendingFriendPreviewUrl.value) {
    URL.revokeObjectURL(pendingFriendPreviewUrl.value)
    pendingFriendPreviewUrl.value = ''
  }
}

function revokeYisePendingPreview() {
  if (pendingYisePreviewUrl.value) {
    URL.revokeObjectURL(pendingYisePreviewUrl.value)
    pendingYisePreviewUrl.value = ''
  }
}

function resetPendingFriend() {
  pendingFriendFile.value = null
  revokeFriendPendingPreview()
}

function resetPendingYise() {
  pendingYiseFile.value = null
  revokeYisePendingPreview()
}

const skillMap = computed(() => {
  const map = new Map<number, OpsPokemonOptionItem>()
  for (const item of skills.value) {
    map.set(item.id, item)
  }
  return map
})

const filteredSkills = computed(() => {
  const kw = skillKeyword.value.trim().toLowerCase()
  const rows = form.skills.map((item, index) => {
    const skill = skillMap.value.get(item.skill_id)
    return {
      item,
      realIndex: index,
      skillName: skill?.name || '',
      icon: skill?.icon || '',
    }
  })
  if (!kw) return rows
  return rows.filter((row) => row.skillName.toLowerCase().includes(kw))
})

const skillTotalPages = computed(() => Math.max(1, Math.ceil(filteredSkills.value.length / skillPageSize)))
const pagedSkills = computed(() => {
  const start = (skillPage.value - 1) * skillPageSize
  return filteredSkills.value.slice(start, start + skillPageSize)
})

const filteredSkillCandidates = computed(() => {
  const kw = skillSelectorKeyword.value.trim().toLowerCase()
  if (!kw) return skills.value
  return skills.value.filter((item) => item.name.toLowerCase().includes(kw))
})

const skillSelectorTotalPages = computed(() =>
  Math.max(1, Math.ceil(filteredSkillCandidates.value.length / skillSelectorPageSize))
)
const pagedSkillCandidates = computed(() => {
  const start = (skillSelectorPage.value - 1) * skillSelectorPageSize
  return filteredSkillCandidates.value.slice(start, start + skillSelectorPageSize)
})

const filteredTraitSuggestions = computed(() => {
  const kw = filterTraitKeyword.value.trim().toLowerCase()
  if (!kw) return traits.value.slice(0, 12)
  return traits.value.filter((item) => item.name.toLowerCase().includes(kw)).slice(0, 12)
})

const sortedEvolutionSteps = computed(() =>
  evolutionSteps.value
    .map((step, index) => ({ step, index }))
    .sort((a, b) => (a.step.sort_order || 0) - (b.step.sort_order || 0) || a.index - b.index)
)

const evolutionLevelsForEditor = computed(() => {
  const levels: Array<{ sort_order: number; items: Array<{ step: OpsEvolutionChainStep; index: number }> }> = []
  for (const item of sortedEvolutionSteps.value) {
    const sortOrder = Math.max(1, Number(item.step.sort_order || 1))
    let level = levels.find((x) => x.sort_order === sortOrder)
    if (!level) {
      level = { sort_order: sortOrder, items: [] }
      levels.push(level)
    }
    level.items.push(item)
  }
  return levels
})

function getEvolutionLevelLastIndex(level: { items: Array<{ index: number }> }) {
  return level.items[level.items.length - 1]?.index ?? evolutionSteps.value.length - 1
}

function triggerFriendFilePick() {
  friendFileInputRef.value?.click()
}

function triggerYiseFilePick() {
  yiseFileInputRef.value?.click()
}

function clearFriendImage() {
  resetPendingFriend()
  form.image_lc = ''
}

function clearYiseImage() {
  resetPendingYise()
  form.image_yise = ''
}

function onFriendImageSelected(ev: Event) {
  const el = ev.target as HTMLInputElement
  const file = el.files?.[0]
  if (!file) return
  revokeFriendPendingPreview()
  pendingFriendFile.value = file
  pendingFriendPreviewUrl.value = URL.createObjectURL(file)
  el.value = ''
}

function onYiseImageSelected(ev: Event) {
  const el = ev.target as HTMLInputElement
  const file = el.files?.[0]
  if (!file) return
  revokeYisePendingPreview()
  pendingYiseFile.value = file
  pendingYisePreviewUrl.value = URL.createObjectURL(file)
  el.value = ''
}

function resetForm() {
  editingId.value = null
  form.id = 0
  form.no = ''
  form.name = ''
  form.image = ''
  form.type = ''
  form.type_name = ''
  form.form = ''
  form.form_name = ''
  form.egg_group = ''
  form.trait_id = 0
  form.detail_url = ''
  form.image_lc = ''
  form.image_yise = ''
  resetPendingFriend()
  resetPendingYise()
  form.chain_id = null
  form.hp = 0
  form.atk = 0
  form.matk = 0
  form.def_val = 0
  form.mdef = 0
  form.spd = 0
  form.total_race = 0
  form.obtain_method = ''
  form.attribute_ids = []
  form.egg_groups = []
  form.skills = []
  skillKeyword.value = ''
  evolutionSteps.value = []
  evolutionChainId.value = null
  evolutionSearchKeyword.value = ''
  evolutionPokemonKeyword.value = ''
  evolutionPokemonCandidates.value = []
  evolutionPokemonSearching.value = false
}

function openCreateModal() {
  resetForm()
  skillPage.value = 1
  modalVisible.value = true
}

async function openEditModal(id: number) {
  try {
    const [detail, chain] = await Promise.all([fetchOpsPokemonDetail(id), fetchOpsPokemonEvolutionChain(id)])
    editingId.value = id
    resetPendingFriend()
    resetPendingYise()
    Object.assign(form, detail)
    normalizePokemonSkillTypes()
    evolutionChainId.value = chain.chain_id
    evolutionSteps.value = (chain.steps || []).map((step) => ({
      ...step,
      pre_evolution_condition: step.pre_evolution_condition || '',
    }))
    skillPage.value = 1
    modalVisible.value = true
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '加载详情失败', 'error')
  }
}

function removeEvolutionStep(index: number) {
  evolutionSteps.value.splice(index, 1)
}

function nextEvolutionSortOrder() {
  return Math.max(0, ...evolutionSteps.value.map((step) => Number(step.sort_order || 0))) + 1
}

function hasEvolutionPokemon(name: string) {
  const normalized = name.trim()
  return evolutionSteps.value.some((step) => (step.pokemon_name || '').trim() === normalized)
}

function buildEvolutionStep(name: string, sortOrder = nextEvolutionSortOrder()): OpsEvolutionChainStep {
  return {
    sort_order: sortOrder,
    pokemon_name: name.trim(),
    evolution_condition: '',
    pre_evolution_condition: '',
    image_url: '',
    matched: false,
  }
}

function addCurrentPokemonToEvolution() {
  const ownName = form.name.trim()
  if (!ownName) {
    showOpsToast('当前精灵名称为空，无法添加到进化链', 'error')
    return
  }
  if (hasEvolutionPokemon(ownName)) {
    showOpsToast('当前精灵已在进化链中', 'info')
    return
  }
  evolutionSteps.value.push({
    ...buildEvolutionStep(ownName, evolutionSteps.value.length ? nextEvolutionSortOrder() : 1),
    image_url: friendDisplaySrc.value,
    matched: !!friendDisplaySrc.value,
  })
}

function createEvolutionChainDraft() {
  if (evolutionSteps.value.length) {
    showOpsToast('当前已经有进化链草稿，可继续添加精灵', 'info')
    return
  }
  addCurrentPokemonToEvolution()
}

async function searchEvolutionChain() {
  const kw = evolutionSearchKeyword.value.trim()
  if (!kw) {
    showOpsToast('请输入精灵名称后再搜索', 'error')
    return
  }
  try {
    const chain = await searchOpsPokemonEvolutionChain(kw)
    evolutionChainId.value = chain.chain_id
    evolutionSteps.value = (chain.steps || []).map((step) => ({
      ...step,
      pre_evolution_condition: step.pre_evolution_condition || '',
    }))
    showOpsToast('已加载进化链，可添加或调整当前精灵后保存绑定', 'success')
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '搜索进化链失败', 'error')
  }
}

async function searchEvolutionPokemon() {
  const kw = evolutionPokemonKeyword.value.trim()
  if (!kw) {
    showOpsToast('请输入精灵名称后再搜索', 'error')
    return
  }
  evolutionPokemonSearching.value = true
  try {
    const data = await fetchOpsPokemon({ keyword: kw, page: 1, page_size: 10 })
    evolutionPokemonCandidates.value = data.items
    if (!data.items.length) {
      showOpsToast('未找到匹配精灵', 'info')
    }
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '搜索精灵失败', 'error')
  } finally {
    evolutionPokemonSearching.value = false
  }
}

function addEvolutionPokemon(item: OpsPokemonItem) {
  if (hasEvolutionPokemon(item.name)) {
    showOpsToast('该精灵已在进化链中', 'info')
    return
  }
  evolutionSteps.value.push(buildEvolutionStep(item.name, evolutionSteps.value.length ? nextEvolutionSortOrder() : 1))
}

function dragCurrentPokemon(_e: DragEvent) {
  // marker for drag source
}

function dropCurrentPokemon(targetIndex: number) {
  const ownName = form.name.trim()
  if (!ownName) {
    showOpsToast('当前精灵名称为空，无法插入', 'error')
    return
  }
  const existedIndex = evolutionSteps.value.findIndex((step) => (step.pokemon_name || '').trim() === ownName)
  const existing = existedIndex >= 0 ? evolutionSteps.value[existedIndex] : undefined
  const ownStep: OpsEvolutionChainStep = existing
    ? { ...existing }
    : buildEvolutionStep(ownName, evolutionSteps.value[targetIndex]?.sort_order || nextEvolutionSortOrder())
  if (existedIndex >= 0) {
    evolutionSteps.value.splice(existedIndex, 1)
  }
  const insertIndex = Math.max(0, Math.min(targetIndex, evolutionSteps.value.length))
  evolutionSteps.value.splice(insertIndex, 0, ownStep)
}

function dropCurrentPokemonAfter(targetIndex: number) {
  dropCurrentPokemon(targetIndex + 1)
}

function openEvolutionEditor(index: number) {
  const current = evolutionSteps.value[index]
  if (!current) return
  evolutionEditingIndex.value = index
  evolutionDraft.sort_order = current.sort_order || index + 1
  evolutionDraft.pokemon_name = current.pokemon_name || ''
  evolutionDraft.evolution_condition = current.evolution_condition || ''
  evolutionDraft.pre_evolution_condition = current.pre_evolution_condition || ''
  evolutionDraft.image_url = current.image_url || ''
  evolutionDraft.matched = current.matched ?? false
  evolutionEditorVisible.value = true
}

function closeEvolutionEditor() {
  evolutionEditorVisible.value = false
  evolutionEditingIndex.value = null
}

function saveEvolutionStep() {
  const idx = evolutionEditingIndex.value
  if (idx === null) return
  const name = evolutionDraft.pokemon_name.trim()
  if (!name) {
    showOpsToast('精灵名称不能为空', 'error')
    return
  }
  evolutionSteps.value[idx] = {
    ...evolutionSteps.value[idx],
    pokemon_name: name,
    evolution_condition: evolutionDraft.evolution_condition.trim(),
    pre_evolution_condition: evolutionDraft.pre_evolution_condition.trim(),
    sort_order: Math.max(1, Number(evolutionDraft.sort_order || 1)),
  }
  closeEvolutionEditor()
}

function closeModal() {
  modalVisible.value = false
  skillSelectorVisible.value = false
  evolutionEditorVisible.value = false
  resetPendingFriend()
  resetPendingYise()
}

function isEggGroupSelected(group: string): boolean {
  return form.egg_groups.includes(group)
}

function toggleEggGroup(group: string) {
  if (isEggGroupSelected(group)) {
    form.egg_groups = form.egg_groups.filter((x) => x !== group)
    return
  }
  form.egg_groups = [...form.egg_groups, group]
}

function openSkillSelector() {
  skillSelectorKeyword.value = ''
  skillSelectorPage.value = 1
  skillSelectorVisible.value = true
}

function closeSkillSelector() {
  skillSelectorVisible.value = false
}

function primarySkillSourceCode(): string {
  return skillSourceOptions.value[0]?.code ?? ''
}

function normalizePokemonSkillTypes() {
  const opts = skillSourceOptions.value
  if (!opts.length) return
  for (const s of form.skills) {
    const t = (s.type || '').trim()
    if (!t) {
      s.type = primarySkillSourceCode()
      continue
    }
    if (opts.some((o) => o.code === t)) continue
    const byLabel = opts.find((o) => o.label === t)
    if (byLabel) s.type = byLabel.code
  }
}

function addSkillBySelect(skillId: number) {
  if (form.skills.some((s) => s.skill_id === skillId)) {
    showOpsToast('该技能已在列表中', 'info')
    return
  }
  form.skills.push({ skill_id: skillId, type: primarySkillSourceCode(), sort_order: form.skills.length + 1 })
  skillPage.value = skillTotalPages.value
  skillSelectorVisible.value = false
}

function removeSkillRow(index: number) {
  form.skills.splice(index, 1)
  if (skillPage.value > skillTotalPages.value) {
    skillPage.value = skillTotalPages.value
  }
}

function isAttrSelected(attrId: number): boolean {
  return form.attribute_ids.includes(attrId)
}

function toggleAttribute(attrId: number) {
  if (isAttrSelected(attrId)) {
    form.attribute_ids = form.attribute_ids.filter((id) => id !== attrId)
    return
  }
  if (form.attribute_ids.length >= 2) {
    showOpsToast('属性最多只能选择两种', 'error')
    return
  }
  form.attribute_ids = [...form.attribute_ids, attrId]
}

async function loadOptions() {
  const [result, eggGroupDict, typeDict, formDict, skillSourceDict] = await Promise.all([
    fetchOpsPokemonOptions(),
    fetchOpsDicts({ dict_type: 'egg_group' }),
    fetchOpsDicts({ dict_type: 'pokemon_type' }),
    fetchOpsDicts({ dict_type: 'pokemon_form' }),
    fetchOpsDicts({ dict_type: 'pokemon_skill_source' }),
  ])
  traits.value = result.traits
  attributes.value = result.attributes
  skills.value = result.skills
  eggGroupOptions.value = eggGroupDict.items
    .map((item) => item.label?.trim() || item.code?.trim())
    .filter((x): x is string => !!x)
  typeOptions.value = typeDict.items.map((item) => ({ code: item.code, label: item.label }))
  formOptions.value = formDict.items.map((item) => ({ code: item.code, label: item.label }))
  skillSourceOptions.value = skillSourceDict.items.map((item) => ({
    code: item.code,
    label: item.label,
  }))
  applyTypeLabel()
  applyFormLabel()
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const [me, data] = await Promise.all([
      fetchOpsMe(),
      fetchOpsPokemon({
        no: filterNo.value.trim() || undefined,
        name: filterName.value.trim() || undefined,
        attr_id: typeof filterAttrId.value === 'number' ? filterAttrId.value : undefined,
        egg_group: filterEggGroup.value || undefined,
        type_code: filterTypeCode.value || undefined,
        form_code: filterFormCode.value || undefined,
        trait_id: typeof filterTraitId.value === 'number' ? filterTraitId.value : undefined,
        page: page.value,
        page_size: pageSize,
      }),
    ])
    isAdmin.value = me.role === 'admin'
    total.value = data.total
    totalPages.value = Math.max(1, Math.ceil(data.total / pageSize))
    items.value = data.items
    page.value = data.page
  } catch (err: any) {
    if (err?.response?.status === 401) {
      clearOpsToken()
      return
    }
    error.value = err?.response?.data?.detail || '加载失败'
  } finally {
    loading.value = false
  }
}

async function searchList() {
  page.value = 1
  await loadList()
}

async function resetFilters() {
  filterNo.value = ''
  filterName.value = ''
  filterAttrId.value = ''
  filterEggGroup.value = ''
  filterTypeCode.value = ''
  filterFormCode.value = ''
  filterTraitId.value = ''
  filterTraitKeyword.value = ''
  traitSuggestVisible.value = false
  page.value = 1
  await loadList()
}

function onTraitInputFocus() {
  traitSuggestVisible.value = true
}

function onTraitInput() {
  filterTraitId.value = ''
  traitSuggestVisible.value = true
}

function selectTraitSuggestion(item: OpsPokemonOptionItem) {
  filterTraitId.value = item.id
  filterTraitKeyword.value = item.name
  traitSuggestVisible.value = false
}

function onTraitInputBlur() {
  window.setTimeout(() => {
    traitSuggestVisible.value = false
  }, 120)
  const exact = traits.value.find((x) => x.name === filterTraitKeyword.value.trim())
  if (exact) {
    filterTraitId.value = exact.id
  } else if (!filterTraitKeyword.value.trim()) {
    filterTraitId.value = ''
  }
}

async function submit() {
  if (saving.value) return
  saving.value = true
  error.value = ''
  try {
    if (form.attribute_ids.length === 0 || form.attribute_ids.length > 2) {
      showOpsToast('属性必须选择 1-2 种', 'error')
      return
    }
    if (pendingFriendFile.value) {
      try {
        const data = await uploadOpsFriendImage(pendingFriendFile.value)
        form.image_lc = data.url
        resetPendingFriend()
      } catch (err: any) {
        showOpsToast(err?.response?.data?.detail || '立绘上传失败', 'error')
        return
      }
    }
    if (pendingYiseFile.value) {
      try {
        const data = await uploadOpsYiseImage(pendingYiseFile.value)
        form.image_yise = data.url
        resetPendingYise()
      } catch (err: any) {
        showOpsToast(err?.response?.data?.detail || '异色立绘上传失败', 'error')
        return
      }
    }
    const payload = {
      ...form,
      no: form.no.trim(),
      name: form.name.trim(),
      egg_groups: [...form.egg_groups],
      egg_group: form.egg_groups[0] || '',
      skills: form.skills
        .filter((x) => x.skill_id > 0)
        .map((x: OpsPokemonSkillItem) => ({
          skill_id: x.skill_id,
          type: (x.type || '').trim() || primarySkillSourceCode(),
          sort_order: x.sort_order || 0,
        })),
    }
    let savedId: number
    if (editingId.value) {
      await updateOpsPokemon(editingId.value, payload)
      savedId = editingId.value
      showOpsToast('精灵已更新', 'success')
    } else {
      const created = await createOpsPokemon(payload)
      savedId = created.id
      showOpsToast('精灵已创建', 'success')
    }
    const validEvolutionSteps = evolutionSteps.value
      .map((step) => ({
        sort_order: Math.max(1, Number(step.sort_order || 1)),
        pokemon_name: (step.pokemon_name || '').trim(),
        evolution_condition: (step.evolution_condition || '').trim(),
        pre_evolution_condition: (step.pre_evolution_condition || '').trim(),
      }))
      .filter((step) => step.pokemon_name)
    if (validEvolutionSteps.length > 0) {
      await updateOpsPokemonEvolutionChain(savedId, validEvolutionSteps)
    }
    closeModal()
    await loadList()
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '保存失败'
    showOpsToast(error.value, 'error')
  } finally {
    saving.value = false
  }
}

async function removeItem(id: number, name: string) {
  if (!window.confirm(`确定删除精灵 ${name} 吗？`)) return
  try {
    await deleteOpsPokemon(id)
    showOpsToast('精灵已删除', 'success')
    await loadList()
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '删除失败', 'error')
  }
}

async function openSyncSkillModal(item: OpsPokemonItem) {
  syncSkillModalVisible.value = true
  syncingSkills.value = true
  syncSkillTarget.value = item
  syncSkillResult.value = null
  syncSkillError.value = ''
  try {
    const result = await syncOpsPokemonLkgcSkills(item.id)
    syncSkillResult.value = result
    showOpsToast('技能同步完成', 'success')
    await loadOptions()
    await loadList()
  } catch (err: any) {
    syncSkillError.value = err?.response?.data?.detail || '同步失败'
    showOpsToast(syncSkillError.value, 'error')
  } finally {
    syncingSkills.value = false
  }
}

function closeSyncSkillModal() {
  if (syncingSkills.value) return
  syncSkillModalVisible.value = false
  syncSkillTarget.value = null
  syncSkillResult.value = null
  syncSkillError.value = ''
}

function applyTypeLabel() {
  const matched = typeOptions.value.find((x) => x.code === form.type)
  form.type_name = matched?.label || ''
}

function applyFormLabel() {
  const matched = formOptions.value.find((x) => x.code === form.form)
  form.form_name = matched?.label || ''
}

watch(() => form.type, applyTypeLabel)
watch(() => form.form, applyFormLabel)
watch(skillKeyword, () => {
  skillPage.value = 1
})
watch(skillSelectorKeyword, () => {
  skillSelectorPage.value = 1
})
watch(
  () => [form.hp, form.atk, form.matk, form.def_val, form.mdef, form.spd],
  () => {
    form.total_race =
      Number(form.hp || 0) +
      Number(form.atk || 0) +
      Number(form.matk || 0) +
      Number(form.def_val || 0) +
      Number(form.mdef || 0) +
      Number(form.spd || 0)
  }
)
watch(skillTotalPages, (newVal) => {
  if (skillPage.value > newVal) {
    skillPage.value = newVal
  }
})
watch(skillSourceOptions, () => {
  if (modalVisible.value) normalizePokemonSkillTypes()
})

onMounted(async () => {
  await loadOptions()
  await loadList()
})

onBeforeUnmount(() => {
  revokeFriendPendingPreview()
  revokeYisePendingPreview()
})
</script>

<template>
  <div class="ops-page">
    <section class="ops-card-padded">
      <div class="ops-filter-bar" style="align-items:flex-end;flex-wrap:wrap;">
        <label class="ops-form-item" style="min-width:200px;">
          <span class="ops-filter-label">精灵编号</span>
          <input v-model="filterNo" class="ops-input" type="text" placeholder="请输入精灵编号" />
        </label>
        <label class="ops-form-item" style="min-width:200px;">
          <span class="ops-filter-label">精灵名称</span>
          <input v-model="filterName" class="ops-input" type="text" placeholder="请输入精灵名称" />
        </label>
        <label class="ops-form-item" style="min-width:160px;">
          <span class="ops-filter-label">属性</span>
          <select v-model="filterAttrId" class="ops-select">
            <option value="">全部属性</option>
            <option v-for="item in attributes" :key="item.id" :value="item.id">{{ item.name }}</option>
          </select>
        </label>
        <label class="ops-form-item" style="min-width:160px;">
          <span class="ops-filter-label">蛋组</span>
          <select v-model="filterEggGroup" class="ops-select">
            <option value="">全部蛋组</option>
            <option v-for="item in eggGroupOptions" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label class="ops-form-item" style="min-width:160px;">
          <span class="ops-filter-label">阶段</span>
          <select v-model="filterTypeCode" class="ops-select">
            <option value="">全部阶段</option>
            <option v-for="item in typeOptions" :key="item.code" :value="item.code">{{ item.label }}</option>
          </select>
        </label>
        <label class="ops-form-item" style="min-width:160px;">
          <span class="ops-filter-label">形态</span>
          <select v-model="filterFormCode" class="ops-select">
            <option value="">全部形态</option>
            <option v-for="item in formOptions" :key="item.code" :value="item.code">{{ item.label }}</option>
          </select>
        </label>
        <label class="ops-form-item" style="min-width:200px;">
          <span class="ops-filter-label">特性</span>
          <div style="position:relative;">
            <input
              v-model="filterTraitKeyword"
              class="ops-input"
              type="text"
              placeholder="输入特性名称"
              @focus="onTraitInputFocus"
              @input="onTraitInput"
              @blur="onTraitInputBlur"
            />
            <div
              v-if="traitSuggestVisible && filteredTraitSuggestions.length"
              style="position:absolute;left:0;right:0;top:calc(100% + 4px);z-index:30;border:1px solid var(--ops-border);border-radius:var(--ops-radius-sm);background:var(--ops-surface);box-shadow:0 8px 20px rgba(15,23,42,0.1);max-height:220px;overflow:auto;"
            >
              <button
                v-for="item in filteredTraitSuggestions"
                :key="item.id"
                type="button"
                class="ops-hover-bg"
                style="width:100%;height:34px;border:none;background:var(--ops-surface);color:var(--ops-text);text-align:left;padding:0 10px;cursor:pointer;font-size:13px;"
                @click="selectTraitSuggestion(item)"
              >
                {{ item.name }}
              </button>
            </div>
          </div>
        </label>
        <div class="ops-filter-actions">
          <button type="button" class="ops-btn ops-btn-primary" @click="searchList">搜索</button>
          <button type="button" class="ops-btn ops-btn-secondary" @click="resetFilters">重置</button>
        </div>
      </div>
    </section>

    <section class="ops-card-padded">
      <div class="ops-toolbar">
        <button type="button" class="ops-btn ops-btn-primary" @click="openCreateModal">新增精灵</button>
        <span class="ops-toolbar-meta">共 {{ total }} 条</span>
      </div>
      <p v-if="error" class="ops-error">{{ error }}</p>
      <div v-if="loading" class="ops-loading">加载中...</div>
      <div v-else-if="!items.length" class="ops-empty">暂无数据</div>
      <div v-else class="ops-table-wrap">
        <table class="ops-table">
          <thead>
            <tr>
              <th>序号</th>
              <th>编号</th>
              <th>名称</th>
              <th>阶段</th>
              <th>形态</th>
              <th>特性</th>
              <th>属性</th>
              <th>蛋组</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ (page - 1) * pageSize + index + 1 }}</td>
              <td>{{ item.no }}</td>
              <td>{{ item.name }}</td>
              <td>{{ item.type_name }}</td>
              <td>{{ item.form_name }}</td>
              <td>{{ item.trait_name }}</td>
              <td>{{ item.attributes.join(' / ') }}</td>
              <td>{{ item.egg_groups.join(' / ') }}</td>
              <td>
                <div class="ops-action-group">
                  <button type="button" class="ops-btn ops-btn-text" @click="openEditModal(item.id)">修改</button>
                  <button type="button" class="ops-btn ops-btn-text" @click="openSyncSkillModal(item)">同步技能</button>
                  <button type="button" class="ops-btn ops-btn-text ops-btn--danger" @click="removeItem(item.id, item.name)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="total > 0" class="ops-pagination">
        <span class="ops-pagination-summary">共 {{ total }} 条，当前显示 {{ pageStart() }}-{{ pageEnd() }} 条</span>
        <div class="ops-pagination-controls">
          <button type="button" class="ops-page-btn" :disabled="page === 1" @click="goToPage(1)">首页</button>
          <button type="button" class="ops-page-btn" :disabled="page === 1" @click="goToPage(page - 1)">上一页</button>
          <button
            v-for="p in visiblePages()"
            :key="p"
            type="button"
            class="ops-page-btn"
            :class="{ 'ops-page-btn--active': p === page }"
            @click="goToPage(p)"
          >
            {{ p }}
          </button>
          <button type="button" class="ops-page-btn" :disabled="page === totalPages" @click="goToPage(page + 1)">下一页</button>
          <button type="button" class="ops-page-btn" :disabled="page === totalPages" @click="goToPage(totalPages)">末页</button>
        </div>
      </div>
    </section>

    <div v-if="modalVisible" class="ops-modal-mask">
      <section class="ops-modal" @click.stop>
        <div class="ops-modal-header">
          <h3>{{ editingId ? '编辑精灵' : '新增精灵' }}</h3>
        </div>
        <form
          style="display:grid;grid-template-columns:1fr;gap:12px;padding:12px 20px 20px;"
          @submit.prevent="submit"
          @keydown.enter.prevent
        >
          <!-- 基础信息 -->
          <section
            style="grid-column:1/-1;border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);padding:12px;background:var(--ops-bg);"
          >
            <h4 style="font-size:14px;color:var(--ops-text);margin:0 0 12px;">基础信息</h4>
            <div
              style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px 20px;align-items:start;"
            >
              <div style="min-width:0;">
                <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 14px;">
                  <label style="display:grid;gap:6px;min-width:0;">
                    <span style="font-size:13px;color:var(--ops-text-secondary);">编号</span>
                    <input v-model="form.no" class="ops-input" required type="text" />
                  </label>
                  <label style="display:grid;gap:6px;min-width:0;">
                    <span style="font-size:13px;color:var(--ops-text-secondary);">名称</span>
                    <input v-model="form.name" class="ops-input" required type="text" />
                  </label>
                  <label style="display:grid;gap:6px;min-width:0;">
                    <span style="font-size:13px;color:var(--ops-text-secondary);">阶段编码</span>
                    <select v-model="form.type" class="ops-select">
                      <option value="">请选择</option>
                      <option v-for="item in typeOptions" :key="item.code" :value="item.code">{{ item.code }}</option>
                    </select>
                  </label>
                  <label style="display:grid;gap:6px;min-width:0;">
                    <span style="font-size:13px;color:var(--ops-text-secondary);">阶段名称</span>
                    <input :value="form.type_name" class="ops-input" type="text" disabled />
                  </label>
                  <label style="display:grid;gap:6px;min-width:0;">
                    <span style="font-size:13px;color:var(--ops-text-secondary);">形态编码</span>
                    <select v-model="form.form" class="ops-select">
                      <option value="">请选择</option>
                      <option v-for="item in formOptions" :key="item.code" :value="item.code">{{ item.code }}</option>
                    </select>
                  </label>
                  <label style="display:grid;gap:6px;min-width:0;">
                    <span style="font-size:13px;color:var(--ops-text-secondary);">形态名称</span>
                    <input :value="form.form_name" class="ops-input" type="text" disabled />
                  </label>
                  <label style="display:grid;gap:6px;min-width:0;">
                    <span style="font-size:13px;color:var(--ops-text-secondary);">特性</span>
                    <select v-model.number="form.trait_id" class="ops-select" required>
                      <option :value="0">请选择</option>
                      <option v-for="t in traits" :key="t.id" :value="t.id">{{ t.name }}</option>
                    </select>
                  </label>
                </div>
              </div>
              <div style="display:flex;gap:12px;position:sticky;top:0;">
                <aside
                  style="width:148px;padding:10px 10px 12px;border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);background:var(--ops-surface);box-shadow:0 1px 2px rgba(0,0,0,0.04);"
                  aria-label="精灵立绘"
                >
                  <div style="font-size:12px;font-weight:600;color:var(--ops-muted);text-transform:uppercase;letter-spacing:0.02em;margin-bottom:8px;">立绘</div>
                  <div style="display:flex;flex-direction:column;gap:8px;align-items:stretch;width:100%;">
                    <button
                      type="button"
                      style="width:100%;aspect-ratio:1;max-height:148px;padding:0;border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);background:var(--ops-bg);cursor:pointer;display:grid;place-items:center;overflow:hidden;"
                      :disabled="saving"
                      @click="triggerFriendFilePick"
                    >
                      <img v-if="friendDisplaySrc" :src="friendDisplaySrc" alt="" style="max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain;" />
                      <div v-else style="display:flex;flex-direction:column;align-items:center;gap:4px;padding:8px;text-align:center;">
                        <span style="font-size:12px;color:var(--ops-text-secondary);">暂无</span>
                        <span style="font-size:11px;color:var(--ops-muted);">点击上传</span>
                      </div>
                    </button>
                    <input
                      ref="friendFileInputRef"
                      type="file"
                      style="position:absolute;width:0;height:0;opacity:0;pointer-events:none;"
                      accept=".webp,.png,.jpg,.jpeg,.gif,image/webp,image/png,image/jpeg,image/gif"
                      :disabled="saving"
                      @change="onFriendImageSelected"
                    />
                    <div style="display:flex;flex-wrap:wrap;gap:6px;justify-content:stretch;">
                      <button type="button" class="ops-btn ops-btn-primary ops-btn-sm" style="flex:1 1 auto;min-width:0;" :disabled="saving" @click="triggerFriendFilePick">
                        {{ friendDisplaySrc ? '更换' : '选择图片' }}
                      </button>
                      <button
                        v-if="form.image_lc || pendingFriendFile"
                        type="button"
                        class="ops-btn ops-btn-secondary ops-btn-sm"
                        :disabled="saving"
                        @click="clearFriendImage"
                      >
                        移除
                      </button>
                    </div>
                  </div>
                </aside>
                <aside
                  style="width:148px;padding:10px 10px 12px;border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);background:var(--ops-surface);box-shadow:0 1px 2px rgba(0,0,0,0.04);"
                  aria-label="异色立绘"
                >
                  <div style="font-size:12px;font-weight:600;color:var(--ops-muted);text-transform:uppercase;letter-spacing:0.02em;margin-bottom:8px;">异色</div>
                  <div style="display:flex;flex-direction:column;gap:8px;align-items:stretch;width:100%;">
                    <button
                      type="button"
                      style="width:100%;aspect-ratio:1;max-height:148px;padding:0;border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);background:var(--ops-bg);cursor:pointer;display:grid;place-items:center;overflow:hidden;"
                      :disabled="saving"
                      @click="triggerYiseFilePick"
                    >
                      <img v-if="yiseDisplaySrc" :src="yiseDisplaySrc" alt="" style="max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain;" />
                      <div v-else style="display:flex;flex-direction:column;align-items:center;gap:4px;padding:8px;text-align:center;">
                        <span style="font-size:12px;color:var(--ops-text-secondary);">暂无</span>
                        <span style="font-size:11px;color:var(--ops-muted);">点击上传</span>
                      </div>
                    </button>
                    <input
                      ref="yiseFileInputRef"
                      type="file"
                      style="position:absolute;width:0;height:0;opacity:0;pointer-events:none;"
                      accept=".webp,.png,.jpg,.jpeg,.gif,image/webp,image/png,image/jpeg,image/gif"
                      :disabled="saving"
                      @change="onYiseImageSelected"
                    />
                    <div style="display:flex;flex-wrap:wrap;gap:6px;justify-content:stretch;">
                      <button type="button" class="ops-btn ops-btn-primary ops-btn-sm" style="flex:1 1 auto;min-width:0;" :disabled="saving" @click="triggerYiseFilePick">
                        {{ yiseDisplaySrc ? '更换' : '选择图片' }}
                      </button>
                      <button
                        v-if="form.image_yise || pendingYiseFile"
                        type="button"
                        class="ops-btn ops-btn-secondary ops-btn-sm"
                        :disabled="saving"
                        @click="clearYiseImage"
                      >
                        移除
                      </button>
                    </div>
                  </div>
                </aside>
              </div>
            </div>
          </section>

          <!-- 种族值 -->
          <section
            style="grid-column:1/-1;border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);padding:12px;background:var(--ops-bg);"
          >
            <h4 style="font-size:14px;color:var(--ops-text);margin:0 0 10px;">种族值</h4>
            <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px 12px;">
              <label style="display:grid;gap:6px;min-width:0;">
                <span style="font-size:13px;color:var(--ops-text-secondary);">HP</span>
                <input v-model.number="form.hp" class="ops-input" type="number" />
              </label>
              <label style="display:grid;gap:6px;min-width:0;">
                <span style="font-size:13px;color:var(--ops-text-secondary);">物攻</span>
                <input v-model.number="form.atk" class="ops-input" type="number" />
              </label>
              <label style="display:grid;gap:6px;min-width:0;">
                <span style="font-size:13px;color:var(--ops-text-secondary);">魔攻</span>
                <input v-model.number="form.matk" class="ops-input" type="number" />
              </label>
              <label style="display:grid;gap:6px;min-width:0;">
                <span style="font-size:13px;color:var(--ops-text-secondary);">物防</span>
                <input v-model.number="form.def_val" class="ops-input" type="number" />
              </label>
              <label style="display:grid;gap:6px;min-width:0;">
                <span style="font-size:13px;color:var(--ops-text-secondary);">魔防</span>
                <input v-model.number="form.mdef" class="ops-input" type="number" />
              </label>
              <label style="display:grid;gap:6px;min-width:0;">
                <span style="font-size:13px;color:var(--ops-text-secondary);">速度</span>
                <input v-model.number="form.spd" class="ops-input" type="number" />
              </label>
              <label style="display:grid;gap:6px;min-width:0;">
                <span style="font-size:13px;color:var(--ops-text-secondary);">总和</span>
                <input :value="form.total_race" class="ops-input" type="number" disabled />
              </label>
            </div>
          </section>

          <!-- 关联信息 -->
          <section
            style="grid-column:1/-1;border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);padding:12px;background:var(--ops-bg);"
          >
            <h4 style="font-size:14px;color:var(--ops-text);margin:0 0 10px;">关联信息</h4>
            <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 14px;">
              <label style="grid-column:1/-1;display:grid;gap:6px;min-width:0;">
                <span style="font-size:13px;color:var(--ops-text-secondary);">蛋组列表</span>
                <div style="display:flex;flex-wrap:wrap;gap:8px;">
                  <button
                    v-for="g in eggGroupOptions"
                    :key="g"
                    type="button"
                    style="height:30px;padding:0 10px;border:1px solid var(--ops-border);border-radius:15px;background:var(--ops-surface);color:var(--ops-text-secondary);cursor:pointer;font-size:12px;"
                    :style="isEggGroupSelected(g) ? {borderColor:'var(--ops-accent)',background:'var(--ops-accent-light)',color:'var(--ops-accent)'} : {}"
                    @click="toggleEggGroup(g)"
                  >
                    {{ g }}
                  </button>
                </div>
              </label>
              <label style="grid-column:1/-1;display:grid;gap:6px;min-width:0;">
                <span style="font-size:13px;color:var(--ops-text-secondary);">属性（最多 2 种）</span>
                <div style="display:flex;flex-wrap:wrap;gap:8px;">
                  <button
                    v-for="a in attributes"
                    :key="a.id"
                    type="button"
                    style="height:30px;padding:0 10px;border:1px solid var(--ops-border);border-radius:15px;background:var(--ops-surface);color:var(--ops-text-secondary);cursor:pointer;font-size:12px;"
                    :style="isAttrSelected(a.id) ? {borderColor:'var(--ops-accent)',background:'var(--ops-accent-light)',color:'var(--ops-accent)'} : {}"
                    @click="toggleAttribute(a.id)"
                  >
                    {{ a.name }}
                  </button>
                </div>
              </label>
            </div>
          </section>

          <!-- 技能列表 -->
          <section
            style="grid-column:1/-1;border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);padding:12px;background:var(--ops-surface);"
          >
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
              <h4 style="font-size:14px;color:var(--ops-text);margin:0;">技能列表</h4>
              <div style="display:flex;align-items:center;gap:8px;">
                <input v-model="skillKeyword" class="ops-input" type="text" placeholder="按技能名称搜索" style="width:220px;" />
                <button type="button" class="ops-btn ops-btn-secondary" @click="openSkillSelector">新增技能</button>
              </div>
            </div>
            <div
              v-for="{ item: s, realIndex, skillName, icon } in pagedSkills"
              :key="realIndex"
              style="display:grid;grid-template-columns:1.8fr 1fr 110px auto;gap:8px;margin-bottom:8px;align-items:center;"
            >
              <div style="height:36px;border:1px solid var(--ops-border);border-radius:var(--ops-radius-sm);display:flex;align-items:center;gap:8px;padding:0 10px;color:var(--ops-text);background:var(--ops-surface);">
                <img v-if="icon" :src="icon" alt="icon" style="width:20px;height:20px;object-fit:contain;border-radius:3px;background:var(--ops-bg);" />
                <span>{{ skillName || `技能ID: ${s.skill_id}` }}</span>
              </div>
              <select v-model="s.type" class="ops-select">
                <option v-for="opt in skillSourceOptions" :key="opt.code" :value="opt.code">{{ opt.label }}</option>
              </select>
              <input v-model.number="s.sort_order" class="ops-input" type="number" placeholder="排序" />
              <button type="button" class="ops-btn ops-btn-text ops-btn--danger" @click="removeSkillRow(realIndex)">删除</button>
            </div>
            <div style="display:flex;align-items:center;justify-content:flex-end;gap:10px;margin-top:6px;color:var(--ops-text-secondary);font-size:13px;">
              <button type="button" class="ops-page-btn" :disabled="skillPage === 1" @click="skillPage -= 1">上一页</button>
              <span>第 {{ skillPage }} / {{ skillTotalPages }} 页</span>
              <button
                type="button"
                class="ops-page-btn"
                :disabled="skillPage >= skillTotalPages"
                @click="skillPage += 1"
              >
                下一页
              </button>
            </div>
          </section>

          <!-- 进化链 -->
          <section
            style="grid-column:1/-1;border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);padding:12px;background:var(--ops-bg);"
          >
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
              <h4 style="font-size:14px;color:var(--ops-text);margin:0;">进化链（链ID：{{ evolutionChainId ?? '未设置' }}）</h4>
              <div style="display:flex;align-items:center;gap:8px;">
                <input
                  v-model="evolutionSearchKeyword"
                  class="ops-input"
                  type="text"
                  placeholder="按精灵名称搜索进化链"
                  style="width:220px;"
                />
                <button type="button" class="ops-btn ops-btn-secondary" @click="searchEvolutionChain">搜索进化链</button>
                <button type="button" class="ops-btn ops-btn-secondary" @click="createEvolutionChainDraft">新建链草稿</button>
              </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
              <input
                v-model="evolutionPokemonKeyword"
                class="ops-input"
                type="text"
                placeholder="搜索精灵添加到进化链"
                style="width:220px;"
                @keyup.enter="searchEvolutionPokemon"
              />
              <button type="button" class="ops-btn ops-btn-secondary" :disabled="evolutionPokemonSearching" @click="searchEvolutionPokemon">
                {{ evolutionPokemonSearching ? '搜索中...' : '搜索精灵' }}
              </button>
              <button type="button" class="ops-btn ops-btn-secondary" @click="addCurrentPokemonToEvolution">添加当前精灵</button>
            </div>
            <div v-if="evolutionPokemonCandidates.length" style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
              <button
                v-for="item in evolutionPokemonCandidates"
                :key="item.id"
                type="button"
                class="ops-hover-accent"
                style="min-height:34px;border:1px solid var(--ops-border);border-radius:999px;background:var(--ops-surface);color:var(--ops-text);display:inline-flex;align-items:center;gap:6px;padding:0 12px;cursor:pointer;font-size:13px;"
                @click="addEvolutionPokemon(item)"
              >
                <span style="color:var(--ops-muted);font-size:12px;">{{ item.no }}</span>
                <strong>{{ item.name }}</strong>
                <em style="color:var(--ops-muted);font-size:12px;font-style:normal;">{{ item.type_name || '未分类' }}</em>
              </button>
            </div>
            <div style="display:flex;justify-content:flex-end;margin-bottom:10px;">
              <div
                style="width:168px;border:1px dashed var(--ops-accent);border-radius:var(--ops-radius-md);background:linear-gradient(to bottom, #f6faff 0%, #f6faff 72%, #eaf8ea 72%, #eaf8ea 100%);padding:10px;display:grid;gap:8px;cursor:grab;"
                draggable="true"
                @dragstart="dragCurrentPokemon"
              >
                <div style="font-size:12px;color:var(--ops-muted);">当前精灵（拖拽到下方插槽）</div>
                <div style="width:100%;aspect-ratio:1/1;border-radius:6px;background:var(--ops-bg);display:grid;place-items:center;overflow:hidden;">
                  <img
                    v-if="evolutionSteps.find((x) => x.pokemon_name === form.name)?.image_url"
                    :src="evolutionSteps.find((x) => x.pokemon_name === form.name)?.image_url"
                    alt="self"
                    style="max-width:86%;max-height:86%;width:auto;height:auto;object-fit:contain;"
                  />
                  <div v-else style="color:var(--ops-muted);font-size:12px;">未加载图片</div>
                </div>
                <div style="font-size:13px;color:var(--ops-text);font-weight:600;text-align:center;">{{ form.name || '未命名精灵' }}</div>
              </div>
            </div>
            <div v-if="evolutionSteps.length" style="display:grid;gap:10px;">
              <section
                v-for="(level, levelIndex) in evolutionLevelsForEditor"
                :key="level.sort_order"
                style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;"
              >
                <div style="min-width:64px;color:var(--ops-muted);font-size:12px;font-weight:600;">排序 {{ level.sort_order }}</div>
                <div style="display:flex;align-items:stretch;gap:8px;flex-wrap:wrap;">
                  <article
                    v-for="{ step, index: realIndex } in level.items"
                    :key="`${step.pokemon_name}-${realIndex}`"
                    class="ops-hover-card"
                    style="width:160px;min-width:160px;border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);background:var(--ops-surface);padding:10px;display:grid;gap:8px;cursor:pointer;"
                    @click="openEvolutionEditor(realIndex)"
                    @dragover.prevent
                    @drop.prevent="dropCurrentPokemon(realIndex)"
                  >
                    <div style="font-size:12px;color:var(--ops-muted);">第 {{ step.sort_order }} 阶</div>
                    <div style="width:100%;aspect-ratio:1/1;border-radius:6px;background:var(--ops-bg);display:grid;place-items:center;overflow:hidden;">
                      <img v-if="step.image_url" :src="step.image_url" alt="pokemon" style="max-width:86%;max-height:86%;width:auto;height:auto;object-fit:contain;" />
                      <div v-else style="color:var(--ops-muted);font-size:12px;">未匹配</div>
                    </div>
                    <div style="font-size:13px;color:var(--ops-text);font-weight:600;text-align:center;">{{ step.pokemon_name || '未命名' }}</div>
                    <div style="min-height:30px;color:var(--ops-text-secondary);font-size:12px;text-align:center;">进化：{{ step.evolution_condition || '空' }}</div>
                    <div style="min-height:30px;color:var(--ops-text-secondary);font-size:12px;text-align:center;">前置：{{ step.pre_evolution_condition || '空' }}</div>
                    <div style="display:flex;justify-content:center;gap:8px;">
                      <button type="button" class="ops-btn ops-btn-text" style="font-size:13px;" @click.stop="openEvolutionEditor(realIndex)">编辑</button>
                      <button type="button" class="ops-btn ops-btn-text ops-btn--danger" style="font-size:13px;" @click.stop="removeEvolutionStep(realIndex)">删除</button>
                    </div>
                  </article>
                </div>
                <div
                  v-if="levelIndex < evolutionLevelsForEditor.length - 1"
                  class="ops-hover-accent-bg"
                  style="color:var(--ops-muted);font-size:16px;font-weight:600;min-width:24px;height:24px;border-radius:999px;display:grid;place-items:center;cursor:default;"
                  @dragover.prevent
                  @drop.prevent="dropCurrentPokemonAfter(getEvolutionLevelLastIndex(level))"
                >
                  →
                </div>
              </section>
              <div
                class="ops-hover-drop"
                style="min-width:72px;height:92px;border:1px dashed var(--ops-border);border-radius:6px;color:var(--ops-muted);font-size:12px;display:grid;place-items:center;background:var(--ops-bg);"
                @dragover.prevent
                @drop.prevent="dropCurrentPokemon(evolutionSteps.length)"
              >放到末尾</div>
            </div>
            <div v-if="!evolutionSteps.length" class="ops-empty" style="min-height:80px;">可搜索已有进化链，或点击"新建链草稿 / 添加当前精灵"开始配置</div>
          </section>

          <div style="grid-column:1/-1;display:flex;justify-content:center;align-items:center;gap:10px;padding-top:4px;">
            <button type="submit" class="ops-btn ops-btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
            <button type="button" class="ops-btn ops-btn-secondary" @click="closeModal">取消</button>
          </div>
        </form>
      </section>
    </div>

    <!-- 洛克观测技能同步结果 -->
    <div v-if="syncSkillModalVisible" class="ops-modal-mask">
      <section
        style="width:min(100%,760px);max-height:calc(100vh - 48px);overflow:auto;background:var(--ops-surface);border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);"
        @click.stop
      >
        <div class="ops-modal-header">
          <h3>同步技能</h3>
        </div>
        <div style="padding:12px 20px 0;display:grid;gap:12px;">
          <div style="border:1px solid var(--ops-border);border-radius:var(--ops-radius-sm);background:var(--ops-bg);padding:12px;display:grid;gap:6px;">
            <div style="font-size:14px;color:var(--ops-text);font-weight:600;">{{ syncSkillTarget?.name || '未选择精灵' }}</div>
            <div style="font-size:13px;color:var(--ops-text-secondary);">
              从洛克观测拉取详情后，同步 <code>base</code>、<code>bloodline</code>、<code>stone</code> 三类技能到当前精灵。
            </div>
          </div>

          <div v-if="syncingSkills" class="ops-loading" style="min-height:100px;">同步中，请稍候...</div>

          <p v-if="syncSkillError" class="ops-error">{{ syncSkillError }}</p>

          <template v-if="syncSkillResult">
            <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;">
              <div style="border:1px solid var(--ops-border);border-radius:var(--ops-radius-sm);padding:10px;background:var(--ops-bg);">
                <div style="font-size:12px;color:var(--ops-muted);">请求技能</div>
                <strong style="font-size:18px;color:var(--ops-text);">{{ syncSkillResult.request_total }}</strong>
              </div>
              <div style="border:1px solid var(--ops-border);border-radius:var(--ops-radius-sm);padding:10px;background:var(--ops-bg);">
                <div style="font-size:12px;color:var(--ops-muted);">命中 / 新增技能</div>
                <strong style="font-size:18px;color:var(--ops-text);">{{ syncSkillResult.matched_skill_count }} / {{ syncSkillResult.inserted_skill_count }}</strong>
              </div>
              <div style="border:1px solid var(--ops-border);border-radius:var(--ops-radius-sm);padding:10px;background:var(--ops-bg);">
                <div style="font-size:12px;color:var(--ops-muted);">新增 / 更新关系</div>
                <strong style="font-size:18px;color:var(--ops-text);">{{ syncSkillResult.inserted_relation_count }} / {{ syncSkillResult.updated_relation_count }}</strong>
              </div>
            </div>

            <div style="font-size:13px;color:var(--ops-text-secondary);">
              洛克观测匹配：{{ syncSkillResult.lkgc_name || '未知' }}
              <span v-if="syncSkillResult.lkgc_pet_id">（{{ syncSkillResult.lkgc_pet_id }}）</span>
              <span v-if="syncSkillResult.skipped_count">，跳过 {{ syncSkillResult.skipped_count }} 条</span>
            </div>

            <div v-if="syncSkillResult.warnings.length" style="border:1px solid #fed7aa;border-radius:var(--ops-radius-sm);background:#fff7ed;color:#9a3412;padding:10px;display:grid;gap:4px;font-size:13px;">
              <strong>提示</strong>
              <div v-for="(msg, index) in syncSkillResult.warnings" :key="index">{{ msg }}</div>
            </div>

            <div style="border:1px solid var(--ops-border);border-radius:var(--ops-radius-sm);overflow:hidden;">
              <table class="ops-table">
                <thead>
                  <tr>
                    <th>技能</th>
                    <th>来源</th>
                    <th>技能ID</th>
                    <th>状态</th>
                    <th>结果</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, index) in syncSkillResult.items" :key="`${item.name}-${index}`">
                    <td>{{ item.name || '-' }}</td>
                    <td>{{ item.source_type }}</td>
                    <td>{{ item.skill_id ?? '-' }}</td>
                    <td>{{ item.status }}</td>
                    <td>{{ item.message }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-if="!syncSkillResult.items.length" class="ops-empty" style="min-height:60px;">没有可同步的技能</div>
            </div>
          </template>
        </div>
        <div style="display:flex;justify-content:center;align-items:center;gap:10px;padding:12px 20px 20px;">
          <button type="button" class="ops-btn ops-btn-secondary" :disabled="syncingSkills" @click="closeSyncSkillModal">关闭</button>
        </div>
      </section>
    </div>

    <!-- 技能选择器 -->
    <div v-if="skillSelectorVisible" class="ops-modal-mask">
      <section
        style="width:min(100%,700px);max-height:calc(100vh - 48px);overflow:auto;background:var(--ops-surface);border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);"
        @click.stop
      >
        <div class="ops-modal-header">
          <h3>选择技能</h3>
        </div>
        <div style="padding:12px 20px 0;display:grid;gap:10px;">
          <div style="display:flex;justify-content:flex-start;">
            <input v-model="skillSelectorKeyword" class="ops-input" type="text" placeholder="输入技能名称搜索" style="width:280px;" />
          </div>
          <div style="border:1px solid var(--ops-border);border-radius:var(--ops-radius-sm);max-height:340px;overflow:auto;padding:8px;display:grid;gap:8px;">
            <button
              v-for="item in pagedSkillCandidates"
              :key="item.id"
              type="button"
              class="ops-hover-accent"
              style="height:40px;border:1px solid var(--ops-border);border-radius:var(--ops-radius-sm);background:var(--ops-surface);color:var(--ops-text);display:flex;align-items:center;gap:8px;padding:0 10px;cursor:pointer;text-align:left;font-size:13px;"
              @click="addSkillBySelect(item.id)"
            >
              <img v-if="item.icon" :src="item.icon" alt="icon" style="width:20px;height:20px;object-fit:contain;border-radius:3px;background:var(--ops-bg);" />
              <span>{{ item.name }}</span>
            </button>
            <div v-if="!pagedSkillCandidates.length" class="ops-empty" style="min-height:60px;">暂无技能</div>
          </div>
          <div style="display:flex;align-items:center;justify-content:flex-end;gap:10px;color:var(--ops-text-secondary);font-size:13px;">
            <button
              type="button"
              class="ops-page-btn"
              :disabled="skillSelectorPage === 1"
              @click="skillSelectorPage -= 1"
            >
              上一页
            </button>
            <span>第 {{ skillSelectorPage }} / {{ skillSelectorTotalPages }} 页</span>
            <button
              type="button"
              class="ops-page-btn"
              :disabled="skillSelectorPage >= skillSelectorTotalPages"
              @click="skillSelectorPage += 1"
            >
              下一页
            </button>
          </div>
        </div>
        <div style="display:flex;justify-content:center;align-items:center;gap:10px;padding:12px 20px 20px;">
          <button type="button" class="ops-btn ops-btn-secondary" @click="closeSkillSelector">关闭</button>
        </div>
      </section>
    </div>

    <!-- 进化阶段编辑器 -->
    <div v-if="evolutionEditorVisible" class="ops-modal-mask">
      <section
        style="width:min(100%,700px);max-height:calc(100vh - 48px);overflow:auto;background:var(--ops-surface);border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);"
        @click.stop
      >
        <div class="ops-modal-header">
          <h3>编辑进化阶段</h3>
        </div>
        <div style="padding:12px 20px 0;display:grid;gap:10px;">
          <label style="display:grid;gap:6px;">
            <span style="font-size:13px;color:var(--ops-text-secondary);">排序（相同排序表示同一阶段分支）</span>
            <input v-model.number="evolutionDraft.sort_order" class="ops-input" type="number" min="1" />
          </label>
          <label style="display:grid;gap:6px;">
            <span style="font-size:13px;color:var(--ops-text-secondary);">精灵名称</span>
            <input v-model="evolutionDraft.pokemon_name" class="ops-input" type="text" placeholder="请输入精灵名称" />
          </label>
          <label style="display:grid;gap:6px;">
            <span style="font-size:13px;color:var(--ops-text-secondary);">进化条件</span>
            <input v-model="evolutionDraft.evolution_condition" class="ops-input" type="text" placeholder="可为空，如：等级32进化" />
          </label>
          <label style="display:grid;gap:6px;">
            <span style="font-size:13px;color:var(--ops-text-secondary);">前置进化条件</span>
            <input v-model="evolutionDraft.pre_evolution_condition" class="ops-input" type="text" placeholder="可为空，如：完成指定任务" />
          </label>
        </div>
        <div style="display:flex;justify-content:center;align-items:center;gap:10px;padding:12px 20px 20px;">
          <button type="button" class="ops-btn ops-btn-primary" @click="saveEvolutionStep">保存</button>
          <button type="button" class="ops-btn ops-btn-secondary" @click="closeEvolutionEditor">取消</button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.ops-hover-bg:hover { background: var(--ops-bg); }
.ops-hover-accent:hover { border-color: var(--ops-accent); color: var(--ops-accent); }
.ops-hover-card:hover { border-color: var(--ops-accent); box-shadow: var(--ops-shadow-sm); background: var(--ops-bg); }
.ops-hover-drop:hover { border-color: var(--ops-accent); color: var(--ops-accent); background: var(--ops-accent-light); }
.ops-hover-accent-bg:hover { background: var(--ops-accent-light); color: var(--ops-accent); }
</style>
