<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  clearOpsToken,
  createOpsStarlightDuelEpisode,
  deleteOpsStarlightDuelEpisode,
  fetchOpsMe,
  fetchOpsStarlightDuelEpisode,
  fetchOpsStarlightDuelEpisodes,
  searchStarlightDuelPokemon,
  searchStarlightDuelSkills,
  showOpsToast,
  updateOpsStarlightDuelEpisode,
  type OpsStarlightDuelEpisodeListItem,
  type OpsStarlightDuelSearchItem,
} from '@/api/ops'

interface PetForm {
  pet_id: number | null
  pet_name: string
  pet_image: string
  sort_order: number
  skills: Array<{ id: number | null; name: string }>
}

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const items = ref<OpsStarlightDuelEpisodeListItem[]>([])
const editingId = ref<number | null>(null)
const drawerVisible = ref(false)
const currentPage = ref(1)
const pageSize = 10
const total = ref(0)

const form = reactive({
  episode_number: 1,
  title: '',
  strategy_text: '',
  is_active: true,
  pets: [] as PetForm[],
})

const isAdmin = ref(false)
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

// Search state
const petSearchKeyword = ref<Record<number, string>>({})
const petSearchResults = ref<Record<number, OpsStarlightDuelSearchItem[]>>({})
const petSearchVisible = ref<Record<number, boolean>>({})
const skillSearchKeyword = ref<Record<string, string>>({})
const skillSearchResults = ref<Record<string, OpsStarlightDuelSearchItem[]>>({})
const skillSearchVisible = ref<Record<string, boolean>>({})

let petSearchTimer: ReturnType<typeof setTimeout> | undefined
let skillSearchTimer: ReturnType<typeof setTimeout> | undefined

function emptyPet(sortOrder: number): PetForm {
  return {
    pet_id: null, pet_name: '', pet_image: '', sort_order: sortOrder,
    skills: [{ id: null, name: '' }, { id: null, name: '' }, { id: null, name: '' }, { id: null, name: '' }],
  }
}

async function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  await loadData()
}

function resetForm() {
  editingId.value = null
  form.episode_number = 1
  form.title = ''
  form.strategy_text = ''
  form.is_active = true
  form.pets = [emptyPet(1)]
  petSearchKeyword.value = {}
  petSearchResults.value = {}
  petSearchVisible.value = {}
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

async function editItem(item: OpsStarlightDuelEpisodeListItem) {
  try {
    loading.value = true
    const detail = await fetchOpsStarlightDuelEpisode(item.id)
    editingId.value = detail.id
    form.episode_number = detail.episode_number
    form.title = detail.title
    form.strategy_text = detail.strategy_text
    form.is_active = detail.is_active
    form.pets = detail.pets.length > 0
      ? detail.pets.map((p, i) => ({
          pet_id: p.pet_id,
          pet_name: p.pet_name,
          pet_image: p.pet_image,
          sort_order: i + 1,
          skills: [
            { id: p.skill_1_id, name: p.skill_1_name },
            { id: p.skill_2_id, name: p.skill_2_name },
            { id: p.skill_3_id, name: p.skill_3_name },
            { id: p.skill_4_id, name: p.skill_4_name },
          ],
        }))
      : [emptyPet(1)]
    drawerVisible.value = true
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '加载详情失败', 'error')
  } finally {
    loading.value = false
  }
}

function addPet() {
  if (form.pets.length >= 6) return
  form.pets.push(emptyPet(form.pets.length + 1))
}

function removePet(index: number) {
  form.pets.splice(index, 1)
  form.pets.forEach((p, i) => { p.sort_order = i + 1 })
}

// Pet search
function onPetSearchInput(petIndex: number) {
  if (petSearchTimer) clearTimeout(petSearchTimer)
  petSearchTimer = setTimeout(async () => {
    const kw = (petSearchKeyword.value[petIndex] || '').trim()
    if (!kw) {
      petSearchResults.value[petIndex] = []
      petSearchVisible.value[petIndex] = false
      return
    }
    try {
      const res = await searchStarlightDuelPokemon(kw)
      petSearchResults.value[petIndex] = res.items
      petSearchVisible.value[petIndex] = true
    } catch { /* ignore */ }
  }, 300)
}

function selectPet(petIndex: number, item: OpsStarlightDuelSearchItem) {
  const pet = form.pets[petIndex]
  if (!pet) return
  pet.pet_id = item.id
  pet.pet_name = item.name
  pet.pet_image = item.image || ''
  petSearchKeyword.value[petIndex] = ''
  petSearchVisible.value[petIndex] = false
}

function clearPet(petIndex: number) {
  const pet = form.pets[petIndex]
  if (!pet) return
  pet.pet_id = null
  pet.pet_name = ''
  pet.pet_image = ''
}

// Skill search
function skillKey(petIndex: number, skillIndex: number) {
  return `${petIndex}-${skillIndex}`
}

function onSkillSearchInput(petIndex: number, skillIndex: number) {
  if (skillSearchTimer) clearTimeout(skillSearchTimer)
  skillSearchTimer = setTimeout(async () => {
    const key = skillKey(petIndex, skillIndex)
    const kw = (skillSearchKeyword.value[key] || '').trim()
    if (!kw) {
      skillSearchResults.value[key] = []
      skillSearchVisible.value[key] = false
      return
    }
    try {
      const res = await searchStarlightDuelSkills(kw)
      skillSearchResults.value[key] = res.items
      skillSearchVisible.value[key] = true
    } catch { /* ignore */ }
  }, 300)
}

function selectSkill(petIndex: number, skillIndex: number, item: OpsStarlightDuelSearchItem) {
  const pet = form.pets[petIndex]
  if (!pet) return
  pet.skills[skillIndex] = { id: item.id, name: item.name }
  const key = skillKey(petIndex, skillIndex)
  skillSearchKeyword.value[key] = ''
  skillSearchVisible.value[key] = false
}

function clearSkill(petIndex: number, skillIndex: number) {
  const pet = form.pets[petIndex]
  if (!pet) return
  pet.skills[skillIndex] = { id: null, name: '' }
}

function hidePetSearch(petIndex: number) {
  window.setTimeout(() => { petSearchVisible.value[petIndex] = false }, 200)
}

function hideSkillSearch(petIndex: number, skillIndex: number) {
  const key = skillKey(petIndex, skillIndex)
  window.setTimeout(() => { skillSearchVisible.value[key] = false }, 200)
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [me, data] = await Promise.all([
      fetchOpsMe(),
      fetchOpsStarlightDuelEpisodes({ page: currentPage.value, page_size: pageSize }),
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

async function submitForm() {
  if (saving.value) return
  saving.value = true
  error.value = ''
  try {
    const payload = {
      episode_number: Number(form.episode_number),
      title: form.title.trim(),
      strategy_text: form.strategy_text,
      is_active: form.is_active,
      pets: form.pets
        .filter(p => p.pet_id)
        .map((p, i) => ({
          pet_id: p.pet_id!,
          sort_order: i + 1,
          skill_1_id: p.skills[0]?.id || null,
          skill_2_id: p.skills[1]?.id || null,
          skill_3_id: p.skills[2]?.id || null,
          skill_4_id: p.skills[3]?.id || null,
        })),
    }
    if (editingId.value) {
      await updateOpsStarlightDuelEpisode(editingId.value, payload)
      showOpsToast('星光对决已更新', 'success')
    } else {
      await createOpsStarlightDuelEpisode(payload)
      showOpsToast('星光对决已创建', 'success')
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

async function removeItem(item: OpsStarlightDuelEpisodeListItem) {
  if (!isAdmin.value) return
  if (!window.confirm(`确定删除第 ${item.episode_number} 期「${item.title}」吗？`)) return
  try {
    await deleteOpsStarlightDuelEpisode(item.id)
    if (editingId.value === item.id) resetForm()
    await loadData()
    showOpsToast('星光对决已删除', 'success')
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '删除失败'
    showOpsToast(error.value, 'error')
  }
}

onMounted(() => {
  void loadData()
})
</script>

<template>
  <div class="ops-page">
    <section class="table-card">
      <div class="toolbar">
        <button type="button" class="btn-primary" @click="openCreateDrawer">新增</button>
        <div class="toolbar-meta">共 {{ total }} 条</div>
      </div>

      <p v-if="error" class="error">{{ error }}</p>

      <div v-if="loading" class="table-placeholder muted">加载中...</div>
      <div v-else-if="!items.length" class="table-placeholder">
        <strong>暂无数据</strong>
        <span>点击「新增」添加星光对决配置。</span>
      </div>
      <div v-else class="table-wrap">
        <table class="tbl">
          <thead>
            <tr>
              <th class="col-index">序号</th>
              <th>期数</th>
              <th>标题</th>
              <th>状态</th>
              <th class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td>第 {{ item.episode_number }} 期</td>
              <td>{{ item.title || '-' }}</td>
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
          <button v-for="page in visiblePages" :key="page" type="button" class="pager-btn" :class="{ active: page === currentPage }" @click="goToPage(page)">{{ page }}</button>
          <button type="button" class="pager-btn" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">下一页</button>
          <button type="button" class="pager-btn" :disabled="currentPage === totalPages" @click="goToPage(totalPages)">末页</button>
        </div>
      </div>
    </section>

    <div v-if="drawerVisible" class="modal-mask" @click="closeDrawer">
      <section class="modal" @click.stop>
        <div class="modal-head">
          <h2>{{ editingId ? '编辑星光对决' : '新增星光对决' }}</h2>
          <button type="button" class="modal-close" @click="closeDrawer">关闭</button>
        </div>

        <form class="modal-body" @submit.prevent="submitForm">
          <div class="form-grid">
            <label class="form-row">
              <span>期数</span>
              <input v-model.number="form.episode_number" required type="number" min="1" placeholder="第几期" />
            </label>
            <label class="form-row">
              <span>标题</span>
              <input v-model="form.title" type="text" placeholder="本期标题" />
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
            <span>宠物配置</span>
            <button v-if="form.pets.length < 6" type="button" class="btn-small" @click="addPet">+ 添加宠物</button>
          </div>

          <div v-for="(pet, pi) in form.pets" :key="pi" class="pet-card">
            <div class="pet-header">
              <strong>宠物 {{ pi + 1 }}</strong>
              <button v-if="form.pets.length > 1" type="button" class="text-btn danger" @click="removePet(pi)">移除</button>
            </div>

            <!-- Pet selector -->
            <div class="search-field">
              <span class="field-label">选择精灵</span>
              <div v-if="pet.pet_id" class="selected-item">
                <img v-if="pet.pet_image" :src="pet.pet_image" class="selected-img" />
                <span>{{ pet.pet_name }}</span>
                <button type="button" class="clear-btn" @click="clearPet(pi)">&times;</button>
              </div>
              <div v-else class="search-input-wrap">
                <input
                  v-model="petSearchKeyword[pi]"
                  type="text"
                  placeholder="输入精灵名称搜索..."
                  @input="onPetSearchInput(pi)"
                  @focus="onPetSearchInput(pi)"
                  @blur="hidePetSearch(pi)"
                />
                <div v-if="petSearchVisible[pi] && petSearchResults[pi]?.length" class="dropdown">
                  <div
                    v-for="opt in petSearchResults[pi]"
                    :key="opt.id"
                    class="dropdown-item"
                    @mousedown.prevent="selectPet(pi, opt)"
                  >
                    <img v-if="opt.image" :src="opt.image" class="dropdown-img" />
                    <span>{{ opt.name }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Skill selectors -->
            <div class="pet-skills">
              <div v-for="si in 4" :key="si" class="search-field skill-field">
                <span class="field-label">技能{{ si }}</span>
                <div v-if="pet.skills[si - 1]?.id" class="selected-item small">
                  <span>{{ pet.skills[si - 1]!.name }}</span>
                  <button type="button" class="clear-btn" @click="clearSkill(pi, si - 1)">&times;</button>
                </div>
                <div v-else class="search-input-wrap">
                  <input
                    v-model="skillSearchKeyword[skillKey(pi, si - 1)]"
                    type="text"
                    placeholder="搜索技能..."
                    @input="onSkillSearchInput(pi, si - 1)"
                    @focus="onSkillSearchInput(pi, si - 1)"
                    @blur="hideSkillSearch(pi, si - 1)"
                  />
                  <div v-if="skillSearchVisible[skillKey(pi, si - 1)] && skillSearchResults[skillKey(pi, si - 1)]?.length" class="dropdown">
                    <div
                      v-for="opt in skillSearchResults[skillKey(pi, si - 1)]"
                      :key="opt.id"
                      class="dropdown-item"
                      @mousedown.prevent="selectSkill(pi, si - 1, opt)"
                    >
                      <span>{{ opt.name }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="section-title"><span>打法说明</span></div>
          <textarea v-model="form.strategy_text" rows="6" placeholder="请输入打法说明..." class="strategy-textarea"></textarea>

          <div class="modal-footer">
            <div class="form-actions">
              <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
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

.table-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 2px;
  padding: 16px 20px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.toolbar-meta { font-size: 13px; color: #909399; }

.form-actions { display: flex; align-items: center; justify-content: center; gap: 12px; }

.btn-primary, .btn-secondary {
  height: 36px; padding: 0 14px; border-radius: 2px;
  cursor: pointer; font-size: 13px;
  transition: border-color 0.15s ease, background-color 0.15s ease, color 0.15s ease;
}
.btn-primary { border: 1px solid #409eff; background: #409eff; color: #fff; }
.btn-primary:hover { background: #66b1ff; border-color: #66b1ff; }
.btn-secondary { border: 1px solid #dcdfe6; background: #fff; color: #606266; }
.btn-secondary:hover { color: #409eff; border-color: #c6e2ff; background: #ecf5ff; }

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

input, select {
  height: 36px; border: 1px solid #dcdfe6; border-radius: 4px;
  background: #fff; color: #303133; padding: 0 14px;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}
input:focus, select:focus {
  outline: none; border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.12);
}

.modal-mask {
  position: fixed; inset: 0; background: rgba(15, 23, 42, 0.34);
  display: grid; place-items: center; padding: 24px; z-index: 1000;
}

.modal {
  width: min(100%, 780px); max-height: calc(100vh - 48px);
  background: #fff; border: 1px solid #ebeef5; border-radius: 4px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
  display: grid; grid-template-rows: auto 1fr; overflow: hidden;
}

.modal-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; padding: 18px 20px;
}
.modal-head h2 { font-size: 16px; font-weight: 600; color: #303133; }
.modal-close { border: none; background: transparent; color: #909399; cursor: pointer; font-size: 13px; }
.modal-close:hover { color: #409eff; }

.modal-body { padding: 8px 20px 20px; overflow: auto; }

.form-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px 20px; }
.form-row { display: grid; grid-template-columns: 48px minmax(0, 1fr); align-items: center; gap: 10px; }
.form-row span { color: #606266; font-size: 13px; }
.form-row input, .form-row select { width: 100%; }

.section-title {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 20px; margin-bottom: 12px;
  padding-bottom: 8px; border-bottom: 1px solid #ebeef5;
}
.section-title span { font-size: 14px; font-weight: 600; color: #303133; }

.pet-card {
  border: 1px solid #ebeef5; border-radius: 4px;
  padding: 12px 16px; margin-bottom: 12px; background: #fafafa;
}
.pet-header {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;
}
.pet-header strong { font-size: 13px; color: #303133; }

.pet-skills {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.search-field {
  position: relative;
  margin-bottom: 8px;
}

.skill-field {
  margin-bottom: 0;
}

.field-label {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.search-input-wrap {
  position: relative;
}

.search-input-wrap input {
  width: 100%;
  height: 32px;
  font-size: 13px;
}

.dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  max-height: 200px;
  overflow: auto;
  z-index: 10;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  color: #303133;
}

.dropdown-item:hover {
  background: #f5f7fa;
}

.dropdown-img {
  width: 28px;
  height: 28px;
  border-radius: 4px;
  object-fit: contain;
}

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
}

.selected-item.small {
  padding: 2px 8px;
  font-size: 12px;
}

.selected-img {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  object-fit: contain;
}

.clear-btn {
  border: none;
  background: transparent;
  color: #909399;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  padding: 0 2px;
}

.clear-btn:hover {
  color: #f56c6c;
}

.strategy-textarea {
  width: 100%; border: 1px solid #dcdfe6; border-radius: 4px;
  padding: 10px 14px; font-size: 13px; color: #303133;
  resize: vertical; transition: border-color 0.18s ease;
}
.strategy-textarea:focus {
  outline: none; border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.12);
}

.modal-footer { margin-top: 20px; padding-top: 4px; }

@media (max-width: 960px) {
  .form-grid { grid-template-columns: 1fr; }
  .form-row { grid-template-columns: 1fr; gap: 8px; }
  .pet-skills { grid-template-columns: repeat(2, 1fr); }
  .modal { width: 100%; }
}
</style>
