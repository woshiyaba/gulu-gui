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
  updateOpsPokemonEvolutionChain,
  updateOpsPokemon,
  uploadOpsFriendImage,
  type OpsEvolutionChainStep,
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

const traits = ref<OpsPokemonOptionItem[]>([])
const attributes = ref<OpsPokemonOptionItem[]>([])
const skills = ref<OpsPokemonOptionItem[]>([])
const eggGroupOptions = ref<string[]>([])
const typeOptions = ref<Array<{ code: string; label: string }>>([])
const formOptions = ref<Array<{ code: string; label: string }>>([])

const skillPage = ref(1)
const skillPageSize = 8
const skillKeyword = ref('')
const skillSelectorVisible = ref(false)
const skillSelectorKeyword = ref('')
const skillSelectorPage = ref(1)
const skillSelectorPageSize = 10
const evolutionSteps = ref<OpsEvolutionChainStep[]>([])
const evolutionChainId = ref<number | null>(null)
const evolutionSearchKeyword = ref('')
/** 已选但未保存的图片（保存时再上传） */
const pendingFriendFile = ref<File | null>(null)
const pendingFriendPreviewUrl = ref('')
const friendFileInputRef = ref<HTMLInputElement | null>(null)
const evolutionEditorVisible = ref(false)
const evolutionEditingIndex = ref<number | null>(null)
const evolutionDraft = reactive<OpsEvolutionChainStep>({
  sort_order: 1,
  pokemon_name: '',
  evolution_condition: '',
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

function revokeFriendPendingPreview() {
  if (pendingFriendPreviewUrl.value) {
    URL.revokeObjectURL(pendingFriendPreviewUrl.value)
    pendingFriendPreviewUrl.value = ''
  }
}

function resetPendingFriend() {
  pendingFriendFile.value = null
  revokeFriendPendingPreview()
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

function triggerFriendFilePick() {
  friendFileInputRef.value?.click()
}

function clearFriendImage() {
  resetPendingFriend()
  form.image_lc = ''
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
  resetPendingFriend()
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
    Object.assign(form, detail)
    evolutionChainId.value = chain.chain_id
    evolutionSteps.value = (chain.steps || []).map((step) => ({ ...step }))
    skillPage.value = 1
    modalVisible.value = true
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '加载详情失败', 'error')
  }
}

function removeEvolutionStep(index: number) {
  evolutionSteps.value.splice(index, 1)
  evolutionSteps.value = evolutionSteps.value.map((step, idx) => ({ ...step, sort_order: idx + 1 }))
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
    evolutionSteps.value = (chain.steps || []).map((step) => ({ ...step }))
    showOpsToast('已加载进化链，可拖拽当前精灵到目标位置', 'success')
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '搜索进化链失败', 'error')
  }
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
    : { sort_order: 1, pokemon_name: ownName, evolution_condition: '', image_url: '', matched: false }
  if (existedIndex >= 0) {
    evolutionSteps.value.splice(existedIndex, 1)
  }
  const insertIndex = Math.max(0, Math.min(targetIndex, evolutionSteps.value.length))
  evolutionSteps.value.splice(insertIndex, 0, ownStep)
  evolutionSteps.value = evolutionSteps.value.map((step, idx) => ({ ...step, sort_order: idx + 1 }))
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
    sort_order: idx + 1,
  }
  closeEvolutionEditor()
}

function closeModal() {
  modalVisible.value = false
  skillSelectorVisible.value = false
  evolutionEditorVisible.value = false
  resetPendingFriend()
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

function addSkillBySelect(skillId: number) {
  if (form.skills.some((s) => s.skill_id === skillId)) {
    showOpsToast('该技能已在列表中', 'info')
    return
  }
  form.skills.push({ skill_id: skillId, type: '原生技能', sort_order: form.skills.length + 1 })
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
  const [result, eggGroupDict, typeDict, formDict] = await Promise.all([
    fetchOpsPokemonOptions(),
    fetchOpsDicts({ dict_type: 'egg_group' }),
    fetchOpsDicts({ dict_type: 'pokemon_type' }),
    fetchOpsDicts({ dict_type: 'pokemon_form' }),
  ])
  traits.value = result.traits
  attributes.value = result.attributes
  skills.value = result.skills
  eggGroupOptions.value = eggGroupDict.items
    .map((item) => item.label?.trim() || item.code?.trim())
    .filter((x): x is string => !!x)
  typeOptions.value = typeDict.items.map((item) => ({ code: item.code, label: item.label }))
  formOptions.value = formDict.items.map((item) => ({ code: item.code, label: item.label }))
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
        form.image_lc = data.image_lc
        resetPendingFriend()
      } catch (err: any) {
        showOpsToast(err?.response?.data?.detail || '图片上传失败', 'error')
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
        .map((x: OpsPokemonSkillItem) => ({ skill_id: x.skill_id, type: x.type || '原生技能', sort_order: x.sort_order || 0 })),
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
      .map((step, idx) => ({
        sort_order: idx + 1,
        pokemon_name: (step.pokemon_name || '').trim(),
        evolution_condition: (step.evolution_condition || '').trim(),
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

onMounted(async () => {
  await loadOptions()
  await loadList()
})

onBeforeUnmount(() => {
  revokeFriendPendingPreview()
})
</script>

<template>
  <div class="ops-page">
    <section class="query-card">
      <div class="query-row">
        <label class="query-item">
          <span class="query-label">精灵编号</span>
          <input v-model="filterNo" class="keyword-input" type="text" placeholder="请输入精灵编号" />
        </label>
        <label class="query-item">
          <span class="query-label">精灵名称</span>
          <input v-model="filterName" class="keyword-input" type="text" placeholder="请输入精灵名称" />
        </label>
        <label class="query-item">
          <span class="query-label">属性</span>
          <select v-model="filterAttrId" class="query-select">
            <option value="">全部属性</option>
            <option v-for="item in attributes" :key="item.id" :value="item.id">{{ item.name }}</option>
          </select>
        </label>
        <label class="query-item">
          <span class="query-label">蛋组</span>
          <select v-model="filterEggGroup" class="query-select">
            <option value="">全部蛋组</option>
            <option v-for="item in eggGroupOptions" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label class="query-item">
          <span class="query-label">阶段</span>
          <select v-model="filterTypeCode" class="query-select">
            <option value="">全部阶段</option>
            <option v-for="item in typeOptions" :key="item.code" :value="item.code">{{ item.label }}</option>
          </select>
        </label>
        <label class="query-item">
          <span class="query-label">形态</span>
          <select v-model="filterFormCode" class="query-select">
            <option value="">全部形态</option>
            <option v-for="item in formOptions" :key="item.code" :value="item.code">{{ item.label }}</option>
          </select>
        </label>
        <label class="query-item">
          <span class="query-label">特性</span>
          <div class="trait-autocomplete">
            <input
              v-model="filterTraitKeyword"
              class="query-select"
              type="text"
              placeholder="输入特性名称"
              @focus="onTraitInputFocus"
              @input="onTraitInput"
              @blur="onTraitInputBlur"
            />
            <div v-if="traitSuggestVisible && filteredTraitSuggestions.length" class="trait-suggest-list">
              <button
                v-for="item in filteredTraitSuggestions"
                :key="item.id"
                type="button"
                class="trait-suggest-item"
                @click="selectTraitSuggestion(item)"
              >
                {{ item.name }}
              </button>
            </div>
          </div>
        </label>
        <div class="query-actions">
          <button type="button" class="btn-primary" @click="searchList">搜索</button>
          <button type="button" class="btn-secondary" @click="resetFilters">重置</button>
        </div>
      </div>
    </section>

    <section class="table-card">
      <div class="toolbar">
        <button type="button" class="btn-primary" @click="openCreateModal">新增精灵</button>
        <div class="toolbar-meta">共 {{ total }} 条</div>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <div v-if="loading" class="placeholder">加载中...</div>
      <div v-else-if="!items.length" class="placeholder">暂无数据</div>
      <div v-else class="table-wrap">
        <table class="tbl">
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
                <button type="button" class="txt-btn" @click="openEditModal(item.id)">修改</button>
                <button type="button" class="txt-btn danger" @click="removeItem(item.id, item.name)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager">
        <div class="pager-summary">共 {{ total }} 条，当前显示 {{ pageStart() }}-{{ pageEnd() }} 条</div>
        <div class="pager-controls">
          <button type="button" class="pager-btn" :disabled="page === 1" @click="goToPage(1)">首页</button>
          <button type="button" class="pager-btn" :disabled="page === 1" @click="goToPage(page - 1)">上一页</button>
          <button
            v-for="p in visiblePages()"
            :key="p"
            type="button"
            class="pager-btn"
            :class="{ active: p === page }"
            @click="goToPage(p)"
          >
            {{ p }}
          </button>
          <button type="button" class="pager-btn" :disabled="page === totalPages" @click="goToPage(page + 1)">下一页</button>
          <button type="button" class="pager-btn" :disabled="page === totalPages" @click="goToPage(totalPages)">末页</button>
        </div>
      </div>
    </section>

    <div v-if="modalVisible" class="modal-mask">
      <section class="modal" @click.stop>
        <div class="modal-head">
          <h3>{{ editingId ? '编辑精灵' : '新增精灵' }}</h3>
        </div>
        <form class="form-grid" @submit.prevent="submit" @keydown.enter.prevent>
          <section class="full section-card section-basic-with-art">
            <h4>基础信息</h4>
            <div class="basic-with-art">
              <div class="basic-with-art-fields">
                <div class="section-grid">
                  <label><span>编号</span><input v-model="form.no" required type="text" /></label>
                  <label><span>名称</span><input v-model="form.name" required type="text" /></label>
                  <label>
                    <span>阶段编码</span>
                    <select v-model="form.type">
                      <option value="">请选择</option>
                      <option v-for="item in typeOptions" :key="item.code" :value="item.code">{{ item.code }}</option>
                    </select>
                  </label>
                  <label><span>阶段名称</span><input :value="form.type_name" type="text" disabled /></label>
                  <label>
                    <span>形态编码</span>
                    <select v-model="form.form">
                      <option value="">请选择</option>
                      <option v-for="item in formOptions" :key="item.code" :value="item.code">{{ item.code }}</option>
                    </select>
                  </label>
                  <label><span>形态名称</span><input :value="form.form_name" type="text" disabled /></label>
                  <label>
                    <span>特性</span>
                    <select v-model.number="form.trait_id" required>
                      <option :value="0">请选择</option>
                      <option v-for="t in traits" :key="t.id" :value="t.id">{{ t.name }}</option>
                    </select>
                  </label>
                </div>
              </div>
              <aside class="basic-with-art-side" aria-label="精灵立绘">
                <div class="basic-art-heading">立绘</div>
                <div class="friend-image-main">
                  <button
                    type="button"
                    class="friend-image-preview"
                    :disabled="saving"
                    @click="triggerFriendFilePick"
                  >
                    <img v-if="friendDisplaySrc" :src="friendDisplaySrc" alt="" class="friend-image-preview-img" />
                    <div v-else class="friend-image-placeholder-inner">
                      <span class="friend-image-placeholder-title">暂无</span>
                      <span class="friend-image-placeholder-sub">点击上传</span>
                    </div>
                  </button>
                  <input
                    ref="friendFileInputRef"
                    type="file"
                    class="friend-file-hidden"
                    accept=".webp,.png,.jpg,.jpeg,.gif,image/webp,image/png,image/jpeg,image/gif"
                    :disabled="saving"
                    @change="onFriendImageSelected"
                  />
                  <div class="friend-image-actions">
                    <button type="button" class="btn-primary btn-compact" :disabled="saving" @click="triggerFriendFilePick">
                      {{ friendDisplaySrc ? '更换' : '选择图片' }}
                    </button>
                    <button
                      v-if="form.image_lc || pendingFriendFile"
                      type="button"
                      class="btn-secondary btn-compact"
                      :disabled="saving"
                      @click="clearFriendImage"
                    >
                      移除
                    </button>
                  </div>
                  <p class="friend-image-note">点击底部「保存」时上传图片并写入数据库</p>
                </div>
              </aside>
            </div>
          </section>

          <section class="full section-card">
            <h4>种族值</h4>
            <div class="stats-grid">
              <label><span>HP</span><input v-model.number="form.hp" type="number" /></label>
              <label><span>物攻</span><input v-model.number="form.atk" type="number" /></label>
              <label><span>魔攻</span><input v-model.number="form.matk" type="number" /></label>
              <label><span>物防</span><input v-model.number="form.def_val" type="number" /></label>
              <label><span>魔防</span><input v-model.number="form.mdef" type="number" /></label>
              <label><span>速度</span><input v-model.number="form.spd" type="number" /></label>
              <label><span>总和</span><input :value="form.total_race" type="number" disabled /></label>
            </div>
          </section>

          <section class="full section-card">
            <h4>关联信息</h4>
            <div class="section-grid">
              <label class="wide">
                <span>蛋组列表</span>
                <div class="attr-picker">
                  <button
                    v-for="g in eggGroupOptions"
                    :key="g"
                    type="button"
                    class="attr-pill"
                    :class="{ active: isEggGroupSelected(g) }"
                    @click="toggleEggGroup(g)"
                  >
                    {{ g }}
                  </button>
                </div>
              </label>
              <label class="wide">
                <span>属性（最多 2 种）</span>
                <div class="attr-picker">
                  <button
                    v-for="a in attributes"
                    :key="a.id"
                    type="button"
                    class="attr-pill"
                    :class="{ active: isAttrSelected(a.id) }"
                    @click="toggleAttribute(a.id)"
                  >
                    {{ a.name }}
                  </button>
                </div>
              </label>
            </div>
          </section>

          <section class="full section-card skill-block">
            <div class="skill-head">
              <h4>技能列表</h4>
              <div class="skill-head-actions">
                <input v-model="skillKeyword" class="skill-search-input" type="text" placeholder="按技能名称搜索" />
                <button type="button" class="btn-secondary" @click="openSkillSelector">新增技能</button>
              </div>
            </div>
            <div v-for="{ item: s, realIndex, skillName, icon } in pagedSkills" :key="realIndex" class="skill-row">
              <div class="skill-name-cell">
                <img v-if="icon" :src="icon" alt="icon" class="skill-icon" />
                <span>{{ skillName || `技能ID: ${s.skill_id}` }}</span>
              </div>
              <select v-model="s.type">
                <option value="原生技能">原生技能</option>
                <option value="学习技能">学习技能</option>
              </select>
              <input v-model.number="s.sort_order" type="number" placeholder="排序" />
              <button type="button" class="btn-text danger" @click="removeSkillRow(realIndex)">删除</button>
            </div>
            <div class="skill-pager">
              <button type="button" class="pager-btn" :disabled="skillPage === 1" @click="skillPage -= 1">上一页</button>
              <span>第 {{ skillPage }} / {{ skillTotalPages }} 页</span>
              <button
                type="button"
                class="pager-btn"
                :disabled="skillPage >= skillTotalPages"
                @click="skillPage += 1"
              >
                下一页
              </button>
            </div>
          </section>

          <section class="full section-card">
            <div class="skill-head">
              <h4>进化链（链ID：{{ evolutionChainId ?? '未设置' }}）</h4>
              <div class="skill-head-actions">
                <input
                  v-model="evolutionSearchKeyword"
                  class="skill-search-input"
                  type="text"
                  placeholder="按精灵名称搜索进化链"
                />
                <button type="button" class="btn-secondary" @click="searchEvolutionChain">搜索进化链</button>
              </div>
            </div>
            <div class="evo-topbar">
              <div class="own-pokemon-card" draggable="true" @dragstart="dragCurrentPokemon">
                <div class="evo-stage">当前精灵（拖拽到下方插槽）</div>
                <div class="evo-image-wrap own-image-wrap">
                  <img
                    v-if="evolutionSteps.find((x) => x.pokemon_name === form.name)?.image_url"
                    :src="evolutionSteps.find((x) => x.pokemon_name === form.name)?.image_url"
                    alt="self"
                    class="evo-image"
                  />
                  <div v-else class="evo-image-placeholder">未加载图片</div>
                </div>
                <div class="evo-name">{{ form.name || '未命名精灵' }}</div>
              </div>
            </div>
            <div v-if="evolutionSteps.length" class="evo-flow">
              <template v-for="(step, idx) in evolutionSteps" :key="`${step.pokemon_name}-${idx}`">
                <article
                  class="evo-card"
                  @click="openEvolutionEditor(idx)"
                  @dragover.prevent
                  @drop.prevent="dropCurrentPokemon(idx)"
                >
                  <div class="evo-stage">第 {{ idx + 1 }} 阶</div>
                  <div class="evo-image-wrap">
                    <img v-if="step.image_url" :src="step.image_url" alt="pokemon" class="evo-image" />
                    <div v-else class="evo-image-placeholder">未匹配</div>
                  </div>
                  <div class="evo-name">{{ step.pokemon_name || '未命名' }}</div>
                  <div class="evo-condition">{{ step.evolution_condition || '无进化条件' }}</div>
                  <div class="evo-actions">
                    <button type="button" class="txt-btn" @click.stop="openEvolutionEditor(idx)">编辑</button>
                    <button type="button" class="txt-btn danger" @click.stop="removeEvolutionStep(idx)">删除</button>
                  </div>
                </article>
                <div
                  v-if="idx < evolutionSteps.length - 1"
                  class="evo-arrow"
                  @dragover.prevent
                  @drop.prevent="dropCurrentPokemonAfter(idx)"
                >
                  →
                </div>
              </template>
              <div class="evo-end-drop" @dragover.prevent @drop.prevent="dropCurrentPokemon(evolutionSteps.length)">放到末尾</div>
            </div>
            <div v-if="!evolutionSteps.length" class="placeholder">先搜索进化链，再拖拽当前精灵卡片到目标位置</div>
          </section>

          <div class="full actions">
            <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
            <button type="button" class="btn-secondary" @click="closeModal">取消</button>
          </div>
        </form>
      </section>
    </div>

    <div v-if="skillSelectorVisible" class="modal-mask">
      <section class="selector-modal" @click.stop>
        <div class="modal-head">
          <h3>选择技能</h3>
        </div>
        <div class="selector-body">
          <div class="selector-toolbar">
            <input v-model="skillSelectorKeyword" class="keyword-input" type="text" placeholder="输入技能名称搜索" />
          </div>
          <div class="selector-list">
            <button
              v-for="item in pagedSkillCandidates"
              :key="item.id"
              type="button"
              class="selector-item"
              @click="addSkillBySelect(item.id)"
            >
              <img v-if="item.icon" :src="item.icon" alt="icon" class="skill-icon" />
              <span>{{ item.name }}</span>
            </button>
            <div v-if="!pagedSkillCandidates.length" class="placeholder">暂无技能</div>
          </div>
          <div class="skill-pager">
            <button
              type="button"
              class="pager-btn"
              :disabled="skillSelectorPage === 1"
              @click="skillSelectorPage -= 1"
            >
              上一页
            </button>
            <span>第 {{ skillSelectorPage }} / {{ skillSelectorTotalPages }} 页</span>
            <button
              type="button"
              class="pager-btn"
              :disabled="skillSelectorPage >= skillSelectorTotalPages"
              @click="skillSelectorPage += 1"
            >
              下一页
            </button>
          </div>
        </div>
        <div class="actions">
          <button type="button" class="btn-secondary" @click="closeSkillSelector">关闭</button>
        </div>
      </section>
    </div>

    <div v-if="evolutionEditorVisible" class="modal-mask">
      <section class="selector-modal evolution-editor" @click.stop>
        <div class="modal-head">
          <h3>编辑进化阶段</h3>
        </div>
        <div class="selector-body">
          <label>
            <span>精灵名称</span>
            <input v-model="evolutionDraft.pokemon_name" class="keyword-input" type="text" placeholder="请输入精灵名称" />
          </label>
          <label>
            <span>进化条件</span>
            <input v-model="evolutionDraft.evolution_condition" class="keyword-input" type="text" placeholder="如：等级32进化" />
          </label>
        </div>
        <div class="actions">
          <button type="button" class="btn-primary" @click="saveEvolutionStep">保存</button>
          <button type="button" class="btn-secondary" @click="closeEvolutionEditor">取消</button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.ops-page { display: grid; gap: 16px; }
.query-card, .table-card { background: #fff; border: 1px solid #ebeef5; border-radius: 4px; padding: 16px; }
.query-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.query-item { display: flex; align-items: center; gap: 8px; min-width: 220px; }
.query-label { font-size: 13px; color: #606266; line-height: 1; white-space: nowrap; min-width: 56px; }
.keyword-input, .query-select {
  width: 180px;
  height: 36px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 0 12px;
  color: #606266;
  background: #fff;
}
.query-actions { display: flex; align-items: center; gap: 8px; }
.trait-autocomplete { position: relative; }
.trait-suggest-list {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 4px);
  z-index: 30;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #fff;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.1);
  max-height: 220px;
  overflow: auto;
}
.trait-suggest-item {
  width: 100%;
  height: 34px;
  border: none;
  background: #fff;
  color: #303133;
  text-align: left;
  padding: 0 10px;
  cursor: pointer;
}
.trait-suggest-item:hover { background: #f5f7fa; color: #409eff; }
.toolbar { display: flex; justify-content: space-between; margin-bottom: 12px; }
.toolbar-meta { color: #909399; font-size: 13px; }
.table-wrap { overflow: auto; border: 1px solid #ebeef5; border-radius: 2px; }
.tbl { width: 100%; border-collapse: collapse; font-size: 13px; }
.tbl th, .tbl td { border: 1px solid #ebeef5; padding: 10px; text-align: center; }
.placeholder { min-height: 120px; display: grid; place-items: center; color: #909399; border: 1px dashed #dcdfe6; border-radius: 2px; }
.pager {
  margin-top: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}
.pager-summary { color: #606266; font-size: 13px; }
.pager-controls { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.pager-btn {
  min-width: 36px;
  height: 32px;
  padding: 0 10px;
  border: 1px solid #dcdfe6;
  border-radius: 2px;
  background: #fff;
  color: #606266;
  cursor: pointer;
  font-size: 13px;
}
.pager-btn:hover:not(:disabled) { color: #409eff; border-color: #409eff; }
.pager-btn.active { background: #409eff; border-color: #409eff; color: #fff; }
.pager-btn:disabled { color: #c0c4cc; cursor: not-allowed; border-color: #ebeef5; }
.txt-btn { border: none; background: transparent; color: #409eff; cursor: pointer; margin: 0 4px; }
.txt-btn.danger { color: #f56c6c; }

.btn-primary, .btn-secondary { height: 36px; border-radius: 4px; padding: 0 14px; cursor: pointer; }
.btn-primary { border: 1px solid #409eff; background: #409eff; color: #fff; }
.btn-secondary { border: 1px solid #dcdfe6; background: #fff; color: #606266; }
.btn-text { border: none; background: transparent; color: #909399; cursor: pointer; }
.btn-text.danger { color: #f56c6c; }

.error { color: #fff; background: #f56c6c; border: 1px solid #f56c6c; border-radius: 4px; padding: 10px 12px; margin-bottom: 10px; }

.modal-mask { position: fixed; inset: 0; display: grid; place-items: center; background: rgba(15, 23, 42, 0.36); padding: 24px; z-index: 1000; }
.modal { width: min(100%, 980px); max-height: calc(100vh - 48px); overflow: auto; background: #fff; border: 1px solid #ebeef5; border-radius: 8px; }
.modal-head { display: flex; align-items: center; justify-content: flex-start; padding: 16px 20px; border-bottom: 1px solid #ebeef5; }
.form-grid { display: grid; grid-template-columns: 1fr; gap: 12px; padding: 12px 20px 20px; }
.form-grid label { display: grid; gap: 6px; min-width: 0; }
.form-grid label span { font-size: 13px; color: #606266; }
.form-grid input, .form-grid select { height: 36px; border: 1px solid #dcdfe6; border-radius: 4px; padding: 0 10px; }
.form-grid input:disabled { background: #f5f7fa; color: #909399; cursor: not-allowed; }
.form-grid select[multiple] { height: auto; min-height: 96px; padding: 6px; }
.full { grid-column: 1 / -1; }
.section-card { border: 1px solid #ebeef5; border-radius: 6px; padding: 12px; background: #fcfdff; }
.section-card h4 { font-size: 14px; color: #303133; margin-bottom: 10px; }
.section-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 14px; }
.stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px 12px; }
.section-grid .wide { grid-column: 1 / -1; }
.section-basic-with-art > h4 {
  margin-bottom: 12px;
}
.basic-with-art {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 168px;
  gap: 16px 20px;
  align-items: start;
}
.basic-with-art-fields { min-width: 0; }
.basic-with-art-side {
  position: sticky;
  top: 0;
  padding: 10px 10px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.basic-art-heading {
  font-size: 12px;
  font-weight: 600;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  margin-bottom: 8px;
}
.friend-image-main {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: stretch;
  width: 100%;
}
.friend-file-hidden {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}
.friend-image-preview {
  width: 100%;
  aspect-ratio: 1;
  max-height: 148px;
  padding: 0;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  background: #f5f7fa;
  cursor: pointer;
  display: grid;
  place-items: center;
  overflow: hidden;
  box-sizing: border-box;
}
.friend-image-preview:hover:not(:disabled) {
  border-color: #409eff;
  background: #ecf5ff;
}
.friend-image-preview:disabled {
  cursor: wait;
  opacity: 0.85;
}
.friend-image-preview-img {
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
}
.friend-image-placeholder-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px;
  text-align: center;
}
.friend-image-placeholder-title { font-size: 12px; color: #606266; }
.friend-image-placeholder-sub { font-size: 11px; color: #c0c4cc; }
.friend-image-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: stretch;
}
.friend-image-actions .btn-primary,
.friend-image-actions .btn-secondary {
  flex: 1 1 auto;
  min-width: 0;
}
.btn-compact {
  height: 32px;
  padding: 0 10px;
  font-size: 13px;
}
.friend-image-note {
  margin: 0;
  font-size: 11px;
  color: #c0c4cc;
  line-height: 1.4;
}
@media (max-width: 720px) {
  .basic-with-art {
    grid-template-columns: 1fr;
  }
  .basic-with-art-side {
    position: static;
    max-width: 220px;
  }
}
.attr-picker { display: flex; flex-wrap: wrap; gap: 8px; }
.attr-pill {
  height: 30px;
  padding: 0 10px;
  border: 1px solid #dcdfe6;
  border-radius: 15px;
  background: #fff;
  color: #606266;
  cursor: pointer;
  font-size: 12px;
}
.attr-pill:hover { border-color: #409eff; color: #409eff; }
.attr-pill.active {
  border-color: #409eff;
  background: #ecf5ff;
  color: #409eff;
}
.skill-block { background: #fff; }
.skill-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.skill-head-actions { display: flex; align-items: center; gap: 8px; }
.skill-search-input { width: 220px; height: 36px; border: 1px solid #dcdfe6; border-radius: 4px; padding: 0 10px; }
.skill-row { display: grid; grid-template-columns: 1.8fr 1fr 110px auto; gap: 8px; margin-bottom: 8px; }
.evo-flow { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; overflow-x: hidden; padding-bottom: 4px; }
.evo-topbar { display: flex; justify-content: flex-end; margin-bottom: 10px; }
.own-pokemon-card {
  width: 168px;
  border: 1px dashed #409eff;
  border-radius: 8px;
  background: linear-gradient(to bottom, #f6faff 0%, #f6faff 72%, #eaf8ea 72%, #eaf8ea 100%);
  padding: 10px;
  display: grid;
  gap: 8px;
  cursor: grab;
}
.evo-card {
  width: 160px;
  min-width: 160px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  background: #fff;
  padding: 10px;
  display: grid;
  gap: 8px;
  cursor: pointer;
}
.evo-card:hover { border-color: #409eff; box-shadow: 0 2px 8px rgba(64, 158, 255, 0.12); }
.evo-card:hover { background: #f8fbff; }
.evo-stage { font-size: 12px; color: #909399; }
.evo-image-wrap {
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 6px;
  background: #f5f7fa;
  display: grid;
  place-items: center;
  overflow: hidden;
}
.own-image-wrap { aspect-ratio: 1 / 1; }
.evo-image {
  max-width: 86%;
  max-height: 86%;
  width: auto;
  height: auto;
  object-fit: contain;
}
.evo-image-placeholder { color: #c0c4cc; font-size: 12px; }
.evo-name { font-size: 13px; color: #303133; font-weight: 600; text-align: center; }
.evo-condition { min-height: 30px; color: #606266; font-size: 12px; text-align: center; }
.evo-actions { display: flex; justify-content: center; gap: 8px; }
.evo-arrow {
  color: #909399;
  font-size: 16px;
  font-weight: 600;
  min-width: 24px;
  height: 24px;
  border-radius: 999px;
  display: grid;
  place-items: center;
}
.evo-arrow:hover { background: #ecf5ff; color: #409eff; }
.evo-end-drop {
  min-width: 72px;
  height: 92px;
  border: 1px dashed #c0c4cc;
  border-radius: 6px;
  color: #909399;
  font-size: 12px;
  display: grid;
  place-items: center;
  background: #fafafa;
}
.evo-end-drop:hover { border-color: #409eff; color: #409eff; background: #ecf5ff; }
.skill-name-cell {
  height: 36px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  color: #303133;
  background: #fff;
}
.skill-icon { width: 20px; height: 20px; object-fit: contain; border-radius: 3px; background: #f5f7fa; }
.skill-pager { display: flex; align-items: center; justify-content: flex-end; gap: 10px; margin-top: 6px; color: #606266; font-size: 13px; }
.actions { display: flex; justify-content: center; align-items: center; gap: 10px; padding-top: 4px; }
.selector-modal {
  width: min(100%, 700px);
  max-height: calc(100vh - 48px);
  overflow: auto;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}
.selector-body { padding: 12px 20px 0; display: grid; gap: 10px; }
.selector-toolbar { display: flex; justify-content: flex-start; }
.selector-list {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  max-height: 340px;
  overflow: auto;
  padding: 8px;
  display: grid;
  gap: 8px;
}
.selector-item {
  height: 40px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #fff;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  cursor: pointer;
  text-align: left;
}
.selector-item:hover { border-color: #409eff; color: #409eff; }
.evolution-editor label { display: grid; gap: 6px; }
.evolution-editor label span { font-size: 13px; color: #606266; }

@media (max-width: 960px) {
  .query-row { flex-direction: column; align-items: stretch; }
  .query-item { width: 100%; min-width: 0; }
  .query-label { min-width: 0; }
  .keyword-input, .query-select { width: 100%; }
  .query-actions { width: 100%; }
  .section-grid, .stats-grid { grid-template-columns: 1fr; }
  .skill-row { grid-template-columns: 1fr; }
  .evo-flow { flex-direction: column; align-items: stretch; }
  .evo-topbar { justify-content: stretch; }
  .own-pokemon-card { width: 100%; }
  .evo-end-drop { width: 100%; min-width: 0; height: 40px; }
  .evo-card { width: 100%; min-width: 0; }
  .evo-arrow { transform: rotate(90deg); }
  .skill-head, .skill-head-actions { flex-direction: column; align-items: stretch; }
  .skill-search-input { width: 100%; }
  .pager { align-items: flex-start; flex-direction: column; }
}
</style>
