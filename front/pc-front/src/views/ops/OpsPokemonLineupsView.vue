<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
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
  type OpsPokemonLineupListItem,
  type OpsResonanceMagicItem,
  type OpsPokemonLineupSearchItem,
  type OpsPokemonLineupStatKey,
} from '@/api/ops'

type StatKey = OpsPokemonLineupStatKey | ''

interface MemberForm {
  pokemon_id: number | null
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

async function loadOptions() {
  const results = await Promise.allSettled([
    fetchOpsDicts({ dict_type: BLOODLINE_DICT_TYPE, page: 1, page_size: 100 }),
    fetchOpsPersonalities({ page: 1, page_size: 100 }),
    fetchOpsDicts({ dict_type: STAT_DICT_TYPE, page: 1, page_size: 100 }),
    fetchOpsDicts({ dict_type: LINEUP_TYPE_DICT, page: 1, page_size: 100 }),
    fetchOpsResonanceMagics({ page: 1, page_size: 200 }),
  ])

  if (results[0].status === 'fulfilled') bloodlineOptions.value = results[0].value.items
  if (results[1].status === 'fulfilled') personalityOptions.value = results[1].value.items
  if (results[3].status === 'fulfilled') lineupTypeOptions.value = results[3].value.items
  if (results[4].status === 'fulfilled') resonanceMagicOptions.value = results[4].value.items

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
    form.source_type = detail.source_type
    form.resonance_magic_id = detail.resonance_magic_id
    form.sort_order = detail.sort_order || 1
    form.is_active = detail.is_active
    form.members = detail.members.length > 0
      ? detail.members.map((m, i) => ({
          pokemon_id: m.pokemon_id,
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
    drawerVisible.value = true
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '加载详情失败', 'error')
  } finally {
    loading.value = false
  }
}

function addMember() {
  if (form.members.length >= 6) return
  form.members.push(emptyMember(form.members.length + 1))
}

function removeMember(index: number) {
  form.members.splice(index, 1)
  form.members.forEach((member, idx) => { member.sort_order = idx + 1 })
}

function onPokemonSearchInput(memberIndex: number) {
  if (pokemonSearchTimer) clearTimeout(pokemonSearchTimer)
  pokemonSearchTimer = setTimeout(async () => {
    const kw = (pokemonSearchKeyword.value[memberIndex] || '').trim()
    if (!kw) {
      pokemonSearchResults.value[memberIndex] = []
      pokemonSearchVisible.value[memberIndex] = false
      return
    }
    try {
      const res = await searchPokemonLineupPokemon(kw)
      pokemonSearchResults.value[memberIndex] = res.items
      pokemonSearchVisible.value[memberIndex] = true
    } catch { /* ignore */ }
  }, 300)
}

function selectPokemon(memberIndex: number, item: OpsPokemonLineupSearchItem) {
  const member = form.members[memberIndex]
  if (!member) return
  member.pokemon_id = item.id
  member.pokemon_name = item.name
  member.pokemon_image = item.image || ''
  pokemonSearchKeyword.value[memberIndex] = ''
  pokemonSearchVisible.value[memberIndex] = false
}

function clearPokemon(memberIndex: number) {
  const member = form.members[memberIndex]
  if (!member) return
  member.pokemon_id = null
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
  if (!member.pokemon_id) return `第 ${index + 1} 只精灵未选择`
  const stats = [member.qual_1, member.qual_2, member.qual_3].filter(Boolean)
  if (new Set(stats).size !== stats.length) return `第 ${index + 1} 只精灵资质属性不能重复`
  const skillIds = member.skills.map((skill) => skill.id).filter(Boolean)
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
      source_type: form.source_type.trim(),
      resonance_magic_id: form.resonance_magic_id,
      sort_order: Number(form.sort_order || 1),
      is_active: form.is_active,
      members: form.members.map((member, index) => ({
        pokemon_id: member.pokemon_id!,
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
    <section class="query-card">
      <div class="query-row">
        <label class="query-item">
          <span class="query-label">阵容标题</span>
          <input v-model="keyword" type="text" placeholder="请输入阵容标题" @keyup.enter="search" />
        </label>
        <label class="query-item">
          <span class="query-label">分类</span>
          <select v-model="sourceTypeFilter">
            <option value="">全部</option>
            <option v-for="opt in lineupTypeOptions" :key="opt.id" :value="opt.code">{{ opt.label }}</option>
          </select>
        </label>
        <label class="query-item">
          <span class="query-label">状态</span>
          <select v-model="isActiveFilter">
            <option value="">全部</option>
            <option value="true">启用</option>
            <option value="false">禁用</option>
          </select>
        </label>
        <div class="query-actions">
          <button type="button" class="btn-primary" @click="search">搜索</button>
          <button type="button" class="btn-default" @click="resetFilters">重置</button>
        </div>
      </div>
    </section>

    <section class="table-card">
      <div class="toolbar">
        <button type="button" class="btn-primary" @click="openCreateDrawer">新增</button>
        <div class="toolbar-meta">共 {{ total }} 条</div>
      </div>

      <p v-if="error" class="error">{{ error }}</p>

      <div v-if="loading" class="table-placeholder muted">加载中...</div>
      <div v-else-if="!items.length" class="table-placeholder">
        <strong>暂无数据</strong>
        <span>请调整查询条件后重试，或新增阵容。</span>
      </div>
      <div v-else class="table-wrap">
        <table class="tbl">
          <thead>
            <tr>
              <th class="col-index">序号</th>
              <th>标题</th>
              <th>分类</th>
              <th>共鸣魔法</th>
              <th>成员数</th>
              <th>排序</th>
              <th>状态</th>
              <th class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td class="label-cell">{{ item.title || '-' }}</td>
              <td>{{ sourceTypeLabel(item.source_type) }}</td>
              <td>{{ item.resonance_magic_name || '-' }}</td>
              <td>{{ item.member_count }}</td>
              <td>{{ item.sort_order }}</td>
              <td>
                <span :class="item.is_active ? 'tag-active' : 'tag-inactive'">
                  {{ item.is_active ? '启用' : '禁用' }}
                </span>
              </td>
              <td>
                <div class="action-group">
                  <button type="button" class="text-btn" @click="editItem(item)">修改</button>
                  <button v-if="isAdmin" type="button" class="text-btn danger" @click="removeItem(item)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="total > 0" class="pagination">
        <div class="pagination-summary">共 {{ total }} 条，当前显示 {{ pageStart }}-{{ pageEnd }} 条</div>
        <div class="pagination-controls">
          <button type="button" class="pager-btn" :disabled="currentPage === 1" @click="goToPage(1)">首页</button>
          <button type="button" class="pager-btn" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">上一页</button>
          <button
            v-for="page in visiblePages"
            :key="page"
            type="button"
            class="pager-btn"
            :class="{ active: page === currentPage }"
            @click="goToPage(page)"
          >{{ page }}</button>
          <button type="button" class="pager-btn" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">下一页</button>
          <button type="button" class="pager-btn" :disabled="currentPage === totalPages" @click="goToPage(totalPages)">末页</button>
        </div>
      </div>
    </section>

    <div v-if="drawerVisible" class="modal-mask">
      <section class="modal" @click.stop>
        <div class="modal-head">
          <h2>{{ editingId ? '编辑精灵阵容' : '新增精灵阵容' }}</h2>
          <button type="button" class="modal-close" @click="closeDrawer">关闭</button>
        </div>

        <form class="modal-body" @submit.prevent>
          <div class="form-grid">
            <label class="form-row">
              <span>标题</span>
              <input v-model="form.title" required type="text" maxlength="50" placeholder="请输入阵容标题" />
            </label>
            <label class="form-row">
              <span>分类</span>
              <select v-model="form.source_type">
                <option value="">未设置</option>
                <option v-for="opt in lineupTypeOptions" :key="opt.id" :value="opt.code">{{ opt.label }}</option>
              </select>
            </label>
            <label class="form-row">
              <span>排序</span>
              <input v-model.number="form.sort_order" type="number" min="1" placeholder="默认 1" />
            </label>
            <label class="form-row">
              <span>共鸣</span>
              <select v-model="form.resonance_magic_id">
                <option :value="null">未设置</option>
                <option v-for="opt in resonanceMagicOptions" :key="opt.id" :value="opt.id">{{ opt.name }}</option>
              </select>
            </label>
            <label class="form-row">
              <span>状态</span>
              <select v-model="form.is_active">
                <option :value="true">启用</option>
                <option :value="false">禁用</option>
              </select>
            </label>
          </div>

          <div class="section-title">
            <span>阵容成员</span>
            <button v-if="form.members.length < 6" type="button" class="btn-small" @click="addMember">+ 添加精灵</button>
          </div>

          <div v-for="(member, mi) in form.members" :key="mi" class="pet-card">
            <div class="pet-header">
              <div class="pet-header-left">
                <div class="pet-avatar">
                  <img v-if="member.pokemon_image" :src="member.pokemon_image" alt="" />
                  <span v-else>#{{ mi + 1 }}</span>
                </div>
                <div class="pet-title">
                  <strong>{{ member.pokemon_name || `精灵 ${mi + 1}` }}</strong>
                  <small>第 {{ mi + 1 }} 只</small>
                </div>
              </div>
              <button v-if="form.members.length > 1" type="button" class="text-btn danger" @click="removeMember(mi)">移除</button>
            </div>

            <div class="pet-grid">
              <div class="form-row search-field">
                <span>精灵</span>
                <div v-if="member.pokemon_id" class="selected-item">
                  <img v-if="member.pokemon_image" :src="member.pokemon_image" class="selected-img" alt="" />
                  <span>{{ member.pokemon_name }}</span>
                  <button type="button" class="clear-btn" @click="clearPokemon(mi)">&times;</button>
                </div>
                <div v-else class="search-input-wrap">
                  <input
                    v-model="pokemonSearchKeyword[mi]"
                    type="text"
                    placeholder="输入精灵名称搜索..."
                    @input="onPokemonSearchInput(mi)"
                    @focus="onPokemonSearchInput(mi)"
                    @blur="hidePokemonSearch(mi)"
                  />
                  <div v-if="pokemonSearchVisible[mi] && pokemonSearchResults[mi]?.length" class="dropdown">
                    <div
                      v-for="opt in pokemonSearchResults[mi]"
                      :key="opt.id"
                      class="dropdown-item"
                      @mousedown.prevent="selectPokemon(mi, opt)"
                    >
                      <img v-if="opt.image" :src="opt.image" class="dropdown-img" alt="" />
                      <span>{{ opt.name }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <label class="form-row">
                <span>血脉</span>
                <select v-model="member.bloodline_dict_id">
                  <option :value="null">未设置</option>
                  <option v-for="opt in bloodlineOptions" :key="opt.id" :value="opt.id">{{ opt.label }}</option>
                </select>
              </label>
              <label class="form-row">
                <span>性格</span>
                <select v-model="member.personality_id">
                  <option :value="null">未设置</option>
                  <option v-for="opt in personalityOptions" :key="opt.id" :value="opt.id">{{ opt.name }}</option>
                </select>
              </label>
            </div>

            <div class="section-subtitle">三项资质</div>
            <div class="quality-grid">
              <select v-model="member.qual_1">
                <option value="">未设置</option>
                <option v-for="opt in statOptions" :key="`q1-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
              </select>
              <select v-model="member.qual_2">
                <option value="">未设置</option>
                <option v-for="opt in statOptions" :key="`q2-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
              </select>
              <select v-model="member.qual_3">
                <option value="">未设置</option>
                <option v-for="opt in statOptions" :key="`q3-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>
            <div class="section-subtitle">技能配置</div>
            <div class="pet-skills">
              <div v-for="si in 4" :key="si" class="form-row search-field skill-field">
                <span>技能{{ si }}</span>
                <div v-if="member.skills[si - 1]?.id" class="selected-item">
                  <img v-if="member.skills[si - 1]?.image" :src="member.skills[si - 1]?.image" class="selected-img" alt="" />
                  <span>{{ member.skills[si - 1]!.name }}</span>
                  <button type="button" class="clear-btn" @click="clearSkill(mi, si - 1)">&times;</button>
                </div>
                <div v-else class="search-input-wrap">
                  <input
                    v-model="skillSearchKeyword[skillKey(mi, si - 1)]"
                    type="text"
                    :placeholder="member.pokemon_id ? '搜索技能...' : '请先选择精灵'"
                    :disabled="!member.pokemon_id"
                    @input="onSkillSearchInput(mi, si - 1)"
                    @focus="onSkillSearchInput(mi, si - 1)"
                    @blur="hideSkillSearch(mi, si - 1)"
                  />
                  <div v-if="skillSearchVisible[skillKey(mi, si - 1)] && skillSearchResults[skillKey(mi, si - 1)]?.length" class="dropdown">
                    <div
                      v-for="opt in skillSearchResults[skillKey(mi, si - 1)]"
                      :key="opt.id"
                      class="dropdown-item"
                      @mousedown.prevent="selectSkill(mi, si - 1, opt)"
                    >
                      <img v-if="opt.image" :src="opt.image" class="dropdown-img" alt="" />
                      <span>{{ opt.name }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="section-subtitle">成员说明</div>
            <textarea v-model="member.member_desc" rows="3" class="desc-textarea" placeholder="请输入该精灵的补充说明..."></textarea>
          </div>

          <div class="section-title"><span>阵容说明</span></div>
          <textarea v-model="form.lineup_desc" rows="5" class="desc-textarea" placeholder="请输入整体阵容说明..."></textarea>

          <div class="modal-footer">
            <div class="form-actions">
              <button type="button" class="btn-primary" :disabled="saving" @click="submitForm">{{ saving ? '保存中...' : '保存' }}</button>
              <button type="button" class="btn-secondary" @click="closeDrawer">取消</button>
            </div>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>

<style scoped>
.ops-page { display: grid; gap: 16px; }

.query-card,
.table-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 2px;
  padding: 16px 20px;
}

.query-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
}

.query-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.query-label { font-size: 13px; color: #606266; white-space: nowrap; }
.query-item input, .query-item select { min-width: 180px; }

.query-actions { display: flex; align-items: center; gap: 10px; margin-left: auto; }

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.toolbar-meta { font-size: 13px; color: #909399; }

.form-actions { display: flex; align-items: center; justify-content: center; gap: 12px; }

.btn-primary, .btn-secondary, .btn-default {
  height: 36px; padding: 0 14px; border-radius: 2px;
  cursor: pointer; font-size: 13px;
  transition: border-color 0.15s ease, background-color 0.15s ease, color 0.15s ease;
}
.btn-primary { border: 1px solid #409eff; background: #409eff; color: #fff; }
.btn-primary:hover { background: #66b1ff; border-color: #66b1ff; }
.btn-secondary, .btn-default { border: 1px solid #dcdfe6; background: #fff; color: #606266; }
.btn-secondary:hover, .btn-default:hover { color: #409eff; border-color: #c6e2ff; background: #ecf5ff; }

.btn-small {
  height: 28px; padding: 0 10px;
  border: 1px solid #409eff; border-radius: 2px;
  background: #ecf5ff; color: #409eff; cursor: pointer; font-size: 12px;
}
.btn-small:hover { background: #409eff; color: #fff; }

.table-wrap { overflow: auto; border: 1px solid #ebeef5; border-radius: 2px; }

.tbl { width: 100%; border-collapse: collapse; font-size: 13px; }
.tbl th, .tbl td {
  padding: 11px 14px; border-bottom: 1px solid #ebeef5; border-right: 1px solid #ebeef5;
  text-align: center; vertical-align: middle;
}
.tbl th:last-child, .tbl td:last-child { border-right: none; }
.tbl thead { background: #fafafa; }
.tbl th { color: #909399; font-weight: 600; }
.tbl tbody tr:hover { background: #f5f7fa; }
.label-cell { text-align: left; color: #303133; }

.col-index { width: 60px; }
.col-actions { width: 140px; }
.tag-active { color: #67c23a; font-size: 13px; }
.tag-inactive { color: #909399; font-size: 13px; }

.action-group { display: inline-flex; align-items: center; justify-content: center; gap: 16px; }
.text-btn { padding: 0; border: none; background: transparent; color: #409eff; cursor: pointer; font-size: 13px; }
.text-btn:hover { color: #66b1ff; }
.text-btn.danger { color: #f56c6c; }
.text-btn.danger:hover { color: #f78989; }

.pagination {
  margin-top: 16px; display: flex; align-items: center;
  justify-content: space-between; gap: 12px;
  padding-top: 16px; border-top: 1px solid #ebeef5; flex-wrap: wrap;
}
.pagination-summary { color: #606266; font-size: 13px; }
.pagination-controls { display: flex; align-items: center; gap: 4px; }

.pager-btn {
  min-width: 36px; height: 32px; padding: 0 10px;
  border: 1px solid #dcdfe6; border-radius: 2px;
  background: #fff; color: #606266; cursor: pointer; font-size: 13px;
}
.pager-btn:hover:not(:disabled) { color: #409eff; border-color: #409eff; }
.pager-btn.active { background: #409eff; border-color: #409eff; color: #fff; }
.pager-btn:disabled { cursor: not-allowed; color: #c0c4cc; border-color: #ebeef5; }

.table-placeholder {
  min-height: 220px; border: 1px dashed #dcdfe6; border-radius: 2px;
  display: grid; place-items: center; text-align: center; color: #909399; padding: 24px;
}
.muted { color: #909399; }
.error {
  color: #dc2626; background: #fef0f0; border: 1px solid #fde2e2;
  border-radius: 4px; padding: 10px 12px; margin-bottom: 12px;
}

input, select, textarea {
  border: 1px solid #dcdfe6; border-radius: 4px;
  background: #fff; color: #303133; padding: 0 14px;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
  font-size: 13px;
}
input, select { height: 36px; }
textarea { padding: 10px 14px; }
input:focus, select:focus, textarea:focus {
  outline: none; border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.12);
}
input:disabled, select:disabled, textarea:disabled {
  background: #f5f7fa; color: #c0c4cc; cursor: not-allowed;
}

.modal-mask {
  position: fixed; inset: 0; background: rgba(15, 23, 42, 0.34);
  display: grid; place-items: center; padding: 24px; z-index: 1000;
}

.modal {
  width: min(100%, 960px); max-height: calc(100vh - 48px);
  background: #fff; border: 1px solid #ebeef5; border-radius: 4px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
  display: grid; grid-template-rows: auto 1fr; overflow: hidden;
}

.modal-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; padding: 18px 20px; border-bottom: 1px solid #ebeef5;
}
.modal-head h2 { font-size: 16px; font-weight: 600; color: #303133; }
.modal-close { border: none; background: transparent; color: #909399; cursor: pointer; font-size: 13px; }
.modal-close:hover { color: #409eff; }

.modal-body { padding: 16px 20px 20px; overflow: auto; }

.form-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px 20px;
}
.form-row {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  align-items: center;
  gap: 6px;
}
.form-row > span { color: #606266; font-size: 13px; }
.form-row input, .form-row select { width: 100%; }

.section-title {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 20px; margin-bottom: 12px;
  padding-bottom: 8px; border-bottom: 1px solid #ebeef5;
}
.section-title span { font-size: 14px; font-weight: 600; color: #303133; }

.section-subtitle { margin: 14px 0 8px; font-size: 13px; font-weight: 600; color: #606266; }

.pet-card {
  border: 1px solid #ebeef5; border-radius: 4px;
  padding: 14px 16px; margin-bottom: 12px; background: #fafafa;
}

.pet-header {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; margin-bottom: 12px;
}
.pet-header-left { display: flex; align-items: center; gap: 10px; }
.pet-avatar {
  width: 40px; height: 40px; border-radius: 4px;
  background: #fff; border: 1px solid #ebeef5;
  display: grid; place-items: center; overflow: hidden;
  font-size: 12px; color: #909399;
}
.pet-avatar img { width: 100%; height: 100%; object-fit: contain; }
.pet-title { display: grid; gap: 2px; }
.pet-title strong { font-size: 14px; color: #303133; }
.pet-title small { font-size: 12px; color: #909399; }

.pet-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px 20px;
  margin-top: 12px;
}

.quality-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.pet-skills {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.search-field { position: relative; }
.skill-field { margin-bottom: 0; }

.search-input-wrap { position: relative; }
.search-input-wrap input { width: 100%; height: 32px; font-size: 13px; }

.dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  max-height: 220px;
  overflow: auto;
  z-index: 10;
}
.dropdown-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; cursor: pointer;
  font-size: 13px; color: #303133;
}
.dropdown-item:hover { background: #f5f7fa; }
.dropdown-img { width: 28px; height: 28px; border-radius: 4px; object-fit: contain; background: #fff; }

.selected-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  border-radius: 4px;
  font-size: 13px;
  color: #409eff;
  max-width: 100%;
}
.selected-item > span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.selected-img { width: 24px; height: 24px; border-radius: 4px; object-fit: contain; background: #fff; }

.clear-btn {
  border: none; background: transparent; color: #909399;
  cursor: pointer; font-size: 16px; line-height: 1; padding: 0 2px;
}
.clear-btn:hover { color: #f56c6c; }

.desc-textarea {
  width: 100%; border: 1px solid #dcdfe6; border-radius: 4px;
  padding: 10px 14px; font-size: 13px; color: #303133;
  resize: vertical;
}
.desc-textarea:focus {
  outline: none; border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.12);
}

.modal-footer { margin-top: 20px; padding-top: 4px; }

@media (max-width: 960px) {
  .form-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .pet-grid { grid-template-columns: 1fr; }
  .quality-grid { grid-template-columns: 1fr 1fr; }
  .pet-skills { grid-template-columns: 1fr 1fr; }
  .modal { width: 100%; }
}

@media (max-width: 640px) {
  .form-grid, .quality-grid, .pet-skills { grid-template-columns: 1fr; }
  .form-row { grid-template-columns: 1fr; gap: 6px; }
  .query-actions { margin-left: 0; }
}
</style>
