<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  clearOpsToken,
  createOpsSkillStone,
  deleteOpsSkillStone,
  fetchOpsMe,
  fetchOpsSkillOptions,
  fetchOpsSkillStoneAvailableSkills,
  fetchOpsSkillStoneDetail,
  fetchOpsSkillStones,
  showOpsToast,
  updateOpsSkillStone,
  type OpsSkillStoneAvailableSkill,
  type OpsSkillStoneItem,
} from '@/api/ops'

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const keyword = ref('')
const attr = ref('')
const type = ref('')
const obtainKeyword = ref('')
const items = ref<OpsSkillStoneItem[]>([])
const editingId = ref<number | null>(null)
const drawerVisible = ref(false)
const currentPage = ref(1)
const pageSize = 10
const total = ref(0)

const attrOptions = ref<string[]>([])
const typeOptions = ref<string[]>([])

const form = reactive({
  skill_id: 0 as number,
  obtain_method: '',
})

const selectedSkill = ref<OpsSkillStoneAvailableSkill | null>(null)
const availableSearch = ref('')
const availableLoading = ref(false)
const availableSkills = ref<OpsSkillStoneAvailableSkill[]>([])
let availableTimer: number | null = null

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const pageStart = computed(() => (total.value === 0 ? 0 : (currentPage.value - 1) * pageSize + 1))
const pageEnd = computed(() => Math.min(currentPage.value * pageSize, total.value))
const visiblePages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  for (let p = start; p <= end; p += 1) pages.push(p)
  return pages
})

function resetForm() {
  editingId.value = null
  form.skill_id = 0
  form.obtain_method = ''
  selectedSkill.value = null
  availableSearch.value = ''
  availableSkills.value = []
}

function openCreateDrawer() {
  resetForm()
  drawerVisible.value = true
  void loadAvailableSkills()
}

function closeDrawer() {
  drawerVisible.value = false
}

async function editItem(item: OpsSkillStoneItem) {
  try {
    const detail = await fetchOpsSkillStoneDetail(item.id)
    editingId.value = detail.id
    form.skill_id = detail.skill_id
    form.obtain_method = detail.obtain_method
    selectedSkill.value = {
      id: detail.skill_id,
      name: detail.skill_name,
      attr: detail.skill_attr,
      type: detail.skill_type,
      icon: detail.skill_icon,
      icon_url: detail.skill_icon_url,
    }
    drawerVisible.value = true
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '加载失败', 'error')
  }
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [me, resp, options] = await Promise.all([
      fetchOpsMe(),
      fetchOpsSkillStones({
        keyword: keyword.value.trim() || undefined,
        attr: attr.value.trim() || undefined,
        type: type.value.trim() || undefined,
        obtain_keyword: obtainKeyword.value.trim() || undefined,
        page: currentPage.value,
        page_size: pageSize,
      }),
      fetchOpsSkillOptions(),
    ])
    void me
    items.value = resp.items
    total.value = resp.total
    currentPage.value = resp.page
    attrOptions.value = options.attrs
    typeOptions.value = options.types
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
  attr.value = ''
  type.value = ''
  obtainKeyword.value = ''
  currentPage.value = 1
  await loadData()
}

async function loadAvailableSkills() {
  availableLoading.value = true
  try {
    const resp = await fetchOpsSkillStoneAvailableSkills({
      keyword: availableSearch.value.trim() || undefined,
      limit: 30,
    })
    availableSkills.value = resp.items
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '加载技能失败', 'error')
  } finally {
    availableLoading.value = false
  }
}

watch(availableSearch, () => {
  if (editingId.value) return
  if (availableTimer) window.clearTimeout(availableTimer)
  availableTimer = window.setTimeout(() => {
    void loadAvailableSkills()
  }, 250)
})

function pickAvailableSkill(skill: OpsSkillStoneAvailableSkill) {
  selectedSkill.value = skill
  form.skill_id = skill.id
}

async function submitForm() {
  if (saving.value) return
  saving.value = true
  error.value = ''
  try {
    if (!editingId.value && !form.skill_id) {
      showOpsToast('请选择技能', 'error')
      return
    }
    if (!form.obtain_method.trim()) {
      showOpsToast('获取方式不能为空', 'error')
      return
    }
    if (editingId.value) {
      await updateOpsSkillStone(editingId.value, { obtain_method: form.obtain_method.trim() })
      showOpsToast('技能石已更新', 'success')
    } else {
      await createOpsSkillStone({
        skill_id: form.skill_id,
        obtain_method: form.obtain_method.trim(),
      })
      showOpsToast('技能石已创建', 'success')
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

async function removeItem(item: OpsSkillStoneItem) {
  if (!window.confirm(`确定删除「${item.skill_name}」的技能石获取方式吗？`)) return
  try {
    await deleteOpsSkillStone(item.id)
    if (editingId.value === item.id) resetForm()
    await loadData()
    showOpsToast('技能石已删除', 'success')
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '删除失败', 'error')
  }
}

onMounted(() => {
  void loadData()
})
</script>

<template>
  <div class="ops-page">
    <section class="query-card">
      <div class="query-row">
        <label class="query-item">
          <span class="query-label">技能名称</span>
          <input v-model="keyword" type="text" placeholder="请输入技能名称" />
        </label>
        <label class="query-item">
          <span class="query-label">属性</span>
          <select v-model="attr">
            <option value="">全部</option>
            <option v-for="opt in attrOptions" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </label>
        <label class="query-item">
          <span class="query-label">类型</span>
          <select v-model="type">
            <option value="">全部</option>
            <option v-for="opt in typeOptions" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </label>
        <label class="query-item">
          <span class="query-label">获取方式</span>
          <input v-model="obtainKeyword" type="text" placeholder="包含的关键词" />
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
        <span>请调整筛选条件后重试，或新增技能石。</span>
      </div>
      <div v-else class="table-wrap">
        <table class="dict-table">
          <thead>
            <tr>
              <th class="col-index">序号</th>
              <th class="col-icon">图标</th>
              <th>技能名称</th>
              <th>属性</th>
              <th>类型</th>
              <th class="col-obtain">获取方式</th>
              <th class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td>
                <img v-if="item.skill_icon_url" :src="item.skill_icon_url" class="icon-thumb" alt="" />
                <span v-else class="muted">-</span>
              </td>
              <td>{{ item.skill_name }}</td>
              <td>{{ item.skill_attr || '-' }}</td>
              <td>{{ item.skill_type || '-' }}</td>
              <td class="obtain-cell" :title="item.obtain_method">{{ item.obtain_method || '-' }}</td>
              <td>
                <div class="action-group">
                  <button type="button" class="text-btn" @click="editItem(item)">修改</button>
                  <button type="button" class="text-btn danger" @click="removeItem(item)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="total > 0" class="pagination">
        <div class="pagination-summary">
          共 {{ total }} 条，当前显示 {{ pageStart }}-{{ pageEnd }} 条
        </div>
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
          >
            {{ page }}
          </button>
          <button
            type="button"
            class="pager-btn"
            :disabled="currentPage === totalPages"
            @click="goToPage(currentPage + 1)"
          >下一页</button>
          <button
            type="button"
            class="pager-btn"
            :disabled="currentPage === totalPages"
            @click="goToPage(totalPages)"
          >末页</button>
        </div>
      </div>
    </section>

    <div v-if="drawerVisible" class="modal-mask" @click="closeDrawer">
      <section class="dict-modal" @click.stop>
        <div class="modal-head">
          <div>
            <h2>{{ editingId ? '编辑技能石' : '新增技能石' }}</h2>
          </div>
          <button type="button" class="modal-close" @click="closeDrawer">关闭</button>
        </div>

        <form class="dict-form" @submit.prevent="submitForm">
          <div class="form-grid">
            <div class="form-row full">
              <span>关联技能</span>
              <div class="skill-slot">
                <div v-if="selectedSkill" class="selected-skill">
                  <img v-if="selectedSkill.icon_url" :src="selectedSkill.icon_url" class="icon-thumb" alt="" />
                  <div class="selected-meta">
                    <strong>{{ selectedSkill.name }}</strong>
                    <small>{{ selectedSkill.attr || '-' }} · {{ selectedSkill.type || '-' }}</small>
                  </div>
                  <span v-if="editingId" class="muted small">（编辑时不可更换技能）</span>
                </div>
                <div v-else class="muted">尚未选择技能</div>

                <div v-if="!editingId" class="skill-picker">
                  <input
                    v-model="availableSearch"
                    type="text"
                    placeholder="搜索未挂技能石的技能"
                  />
                  <div class="skill-options">
                    <div v-if="availableLoading" class="muted">加载中...</div>
                    <div v-else-if="!availableSkills.length" class="muted">暂无可选技能</div>
                    <button
                      v-for="skill in availableSkills"
                      :key="skill.id"
                      type="button"
                      class="skill-option"
                      :class="{ active: selectedSkill?.id === skill.id }"
                      @click="pickAvailableSkill(skill)"
                    >
                      <img v-if="skill.icon_url" :src="skill.icon_url" class="icon-thumb-sm" alt="" />
                      <span class="opt-name">{{ skill.name }}</span>
                      <span class="opt-meta">{{ skill.attr || '-' }} · {{ skill.type || '-' }}</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <label class="form-row full">
              <span>获取方式</span>
              <textarea
                v-model="form.obtain_method"
                rows="3"
                maxlength="255"
                placeholder="例如：XX 使用 YY 指定次数(可在游戏图鉴中查看具体次数)"
              />
            </label>
          </div>
          <div class="modal-footer">
            <div class="form-actions">
              <button type="submit" class="btn-primary" :disabled="saving">
                {{ saving ? '保存中...' : '保存' }}
              </button>
              <button type="button" class="btn-secondary" @click="closeDrawer">取消</button>
            </div>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>

<style scoped>
.ops-page {
  display: grid;
  gap: 16px;
}
.form-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}
.query-card,
.table-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 2px;
  padding: 16px 20px;
}
.query-row,
.toolbar,
.pagination,
.pagination-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}
.query-row {
  flex-wrap: wrap;
}
.query-item {
  display: flex;
  align-items: center;
  gap: 10px;
}
.query-label {
  color: #606266;
  font-size: 13px;
  white-space: nowrap;
}
.query-item input,
.query-item select {
  width: 200px;
}
.query-actions {
  display: flex;
  gap: 10px;
  margin-left: 12px;
}
input,
select,
textarea {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #fff;
  color: #303133;
  padding: 0 14px;
  font-family: inherit;
  font-size: 13px;
}
input,
select {
  height: 36px;
}
textarea {
  padding: 8px 14px;
  min-height: 72px;
  resize: vertical;
}
input:focus,
select:focus,
textarea:focus {
  outline: none;
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.12);
}
.btn-primary,
.btn-default,
.btn-secondary {
  height: 36px;
  padding: 0 14px;
  border-radius: 2px;
  cursor: pointer;
  font-size: 13px;
}
.btn-primary {
  border: 1px solid #409eff;
  background: #409eff;
  color: #fff;
}
.btn-primary:hover {
  background: #66b1ff;
  border-color: #66b1ff;
}
.btn-default,
.btn-secondary {
  border: 1px solid #dcdfe6;
  background: #fff;
  color: #606266;
}
.btn-default:hover,
.btn-secondary:hover {
  color: #409eff;
  border-color: #c6e2ff;
  background: #ecf5ff;
}
.toolbar {
  justify-content: space-between;
  margin-bottom: 12px;
}
.toolbar-meta {
  font-size: 13px;
  color: #909399;
}
.table-wrap {
  overflow: auto;
  border: 1px solid #ebeef5;
  border-radius: 2px;
  background: #fff;
}
.pagination {
  margin-top: 16px;
  justify-content: space-between;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  flex-wrap: wrap;
}
.pagination-summary {
  color: #606266;
  font-size: 13px;
}
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
.pager-btn:hover:not(:disabled) {
  color: #409eff;
  border-color: #409eff;
}
.pager-btn.active {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
}
.pager-btn:disabled {
  cursor: not-allowed;
  color: #c0c4cc;
  border-color: #ebeef5;
}
.table-placeholder {
  min-height: 220px;
  border: 1px dashed #dcdfe6;
  border-radius: 2px;
  display: grid;
  place-items: center;
  text-align: center;
  color: var(--color-muted);
  padding: 24px;
}
.dict-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.dict-table th,
.dict-table td {
  padding: 11px 14px;
  border-bottom: 1px solid #ebeef5;
  border-right: 1px solid #ebeef5;
  text-align: center;
  vertical-align: middle;
}
.dict-table th:last-child,
.dict-table td:last-child {
  border-right: none;
}
.dict-table thead {
  background: #fafafa;
}
.dict-table th {
  color: #909399;
  font-weight: 600;
}
.dict-table tbody tr:hover {
  background: #f5f7fa;
}
.col-index {
  width: 80px;
}
.col-icon {
  width: 72px;
}
.col-obtain {
  max-width: 320px;
  text-align: left;
}
.obtain-cell {
  max-width: 320px;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.col-actions {
  width: 160px;
}
.icon-thumb {
  width: 36px;
  height: 36px;
  object-fit: contain;
  vertical-align: middle;
}
.icon-thumb-sm {
  width: 24px;
  height: 24px;
  object-fit: contain;
}
.action-group {
  display: inline-flex;
  gap: 14px;
  justify-content: center;
}
.text-btn {
  padding: 0;
  border: none;
  background: transparent;
  color: #409eff;
  cursor: pointer;
  font-size: 13px;
}
.text-btn:hover {
  color: #66b1ff;
}
.text-btn.danger {
  color: #f56c6c;
}
.text-btn.danger:hover {
  color: #f78989;
}
.dict-form {
  display: grid;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px 20px;
}
.form-row {
  display: grid;
  grid-template-columns: 90px minmax(0, 1fr);
  align-items: flex-start;
  gap: 10px;
}
.form-row.full {
  grid-column: 1 / -1;
}
.form-row span {
  color: #606266;
  font-size: 13px;
  padding-top: 8px;
}
.form-row input,
.form-row select,
.form-row textarea {
  width: 100%;
}
.skill-slot {
  display: grid;
  gap: 10px;
}
.selected-skill {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #fafafa;
}
.selected-meta {
  display: grid;
  line-height: 1.2;
}
.selected-meta small {
  color: #909399;
  margin-top: 4px;
}
.small {
  font-size: 12px;
}
.skill-picker {
  display: grid;
  gap: 8px;
}
.skill-options {
  max-height: 240px;
  overflow: auto;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #fff;
  padding: 6px;
  display: grid;
  gap: 4px;
}
.skill-option {
  display: grid;
  grid-template-columns: 24px 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  text-align: left;
  font-size: 13px;
  color: #303133;
}
.skill-option:hover {
  background: #f5f7fa;
}
.skill-option.active {
  border-color: #409eff;
  background: #ecf5ff;
  color: #409eff;
}
.opt-meta {
  color: #909399;
  font-size: 12px;
}
.muted {
  color: var(--color-muted);
}
.modal-footer {
  margin-top: 20px;
  padding-top: 4px;
}
.error {
  color: #dc2626;
  background: #fef0f0;
  border: 1px solid #fde2e2;
  border-radius: 4px;
  padding: 10px 12px;
  margin-bottom: 12px;
}
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.34);
  display: grid;
  place-items: center;
  padding: 24px;
  z-index: 1000;
}
.dict-modal {
  width: min(100%, 720px);
  max-height: calc(100vh - 48px);
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
  display: grid;
  grid-template-rows: auto 1fr;
  overflow: hidden;
}
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
}
.modal-head h2 {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.modal-close {
  border: none;
  background: transparent;
  color: #909399;
  cursor: pointer;
  font-size: 13px;
}
.modal-close:hover {
  color: #409eff;
}
.dict-modal form {
  padding: 8px 20px 20px;
  overflow: auto;
}
@media (max-width: 960px) {
  .query-item {
    width: 100%;
    flex-direction: column;
    align-items: flex-start;
  }
  .query-item input,
  .query-item select {
    width: 100%;
  }
  .form-row {
    grid-template-columns: 1fr;
    gap: 8px;
  }
  .dict-modal {
    width: 100%;
  }
}
</style>
