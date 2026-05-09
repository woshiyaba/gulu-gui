<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  clearOpsToken,
  createOpsPokemonFilterOption,
  deleteOpsPokemonFilterOption,
  fetchOpsMe,
  fetchOpsPokemonFilterOptions,
  showOpsToast,
  updateOpsPokemonFilterOption,
  type OpsPokemonFilterOptionItem,
  type OpsPokemonFilterType,
} from '@/api/ops'

const FILTER_TYPE_LABELS: Record<OpsPokemonFilterType, string> = {
  shiny: '异色筛选',
  sort: '排序',
}

const ORDER_BY_OPTIONS = [
  { value: '', label: '（不限）' },
  { value: 'no', label: '编号 no' },
  { value: 'total_stats', label: '总种族值' },
  { value: 'hp', label: '体力 hp' },
  { value: 'atk', label: '攻击 atk' },
  { value: 'matk', label: '魔攻 matk' },
  { value: 'def_val', label: '防御 def_val' },
  { value: 'mdef', label: '魔抗 mdef' },
  { value: 'spd', label: '速度 spd' },
] as const

const ORDER_BY_LABEL_MAP = ORDER_BY_OPTIONS.reduce<Record<string, string>>((acc, item) => {
  acc[item.value] = item.label
  return acc
}, {})

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const keyword = ref('')
const items = ref<OpsPokemonFilterOptionItem[]>([])
const editingId = ref<number | null>(null)
const drawerVisible = ref(false)
const currentPage = ref(1)
const pageSize = 10
const total = ref(0)
const isAdmin = ref(false)

const form = reactive({
  code: '',
  label: '',
  filter_type: 'sort' as OpsPokemonFilterType,
  order_by: 'total_stats',
  order_dir: 'desc' as 'asc' | 'desc' | '',
  sort_order: 0,
  is_active: true,
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const pageStart = computed(() => (total.value === 0 ? 0 : (currentPage.value - 1) * pageSize + 1))
const pageEnd = computed(() => Math.min(currentPage.value * pageSize, total.value))
const visiblePages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  for (let page = start; page <= end; page += 1) {
    pages.push(page)
  }
  return pages
})

const isSortType = computed(() => form.filter_type === 'sort')

function describeOrderBy(value: string) {
  if (!value) return '-'
  return ORDER_BY_LABEL_MAP[value] || value
}

function describeOrderDir(value: string) {
  if (value === 'asc') return '升序'
  if (value === 'desc') return '降序'
  return '-'
}

async function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  await loadData()
}

function resetForm() {
  editingId.value = null
  form.code = ''
  form.label = ''
  form.filter_type = 'sort'
  form.order_by = 'total_stats'
  form.order_dir = 'desc'
  form.sort_order = 0
  form.is_active = true
}

function openCreateDrawer() {
  resetForm()
  drawerVisible.value = true
}

function closeDrawer() {
  drawerVisible.value = false
}

function editItem(item: OpsPokemonFilterOptionItem) {
  editingId.value = item.id
  form.code = item.code
  form.label = item.label
  form.filter_type = item.filter_type
  form.order_by = item.order_by
  form.order_dir = (item.order_dir as 'asc' | 'desc' | '') || ''
  form.sort_order = item.sort_order
  form.is_active = item.is_active
  drawerVisible.value = true
}

function onFilterTypeChange() {
  if (form.filter_type === 'shiny') {
    form.order_by = ''
    form.order_dir = ''
  } else if (form.filter_type === 'sort') {
    if (!form.order_by) form.order_by = 'total_stats'
    if (!form.order_dir) form.order_dir = 'desc'
  }
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [me, list] = await Promise.all([
      fetchOpsMe(),
      fetchOpsPokemonFilterOptions({
        keyword: keyword.value.trim() || undefined,
        page: currentPage.value,
        page_size: pageSize,
      }),
    ])
    isAdmin.value = me.role === 'admin'
    items.value = list.items
    total.value = list.total
    currentPage.value = list.page
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

async function search() {
  currentPage.value = 1
  await loadData()
}

async function resetFilters() {
  keyword.value = ''
  currentPage.value = 1
  await loadData()
}

async function submitForm() {
  if (saving.value) return
  saving.value = true
  error.value = ''
  try {
    const code = form.code.trim()
    const label = form.label.trim()
    if (!code) throw new Error('code 不能为空')
    if (!label) throw new Error('label 不能为空')

    const payload = {
      code,
      label,
      filter_type: form.filter_type,
      order_by: form.filter_type === 'sort' ? form.order_by : '',
      order_dir: form.filter_type === 'sort' ? form.order_dir : '',
      sort_order: Number(form.sort_order) || 0,
      is_active: form.is_active,
    }

    if (form.filter_type === 'sort') {
      if (!payload.order_by) throw new Error('排序类筛选必须选择 order_by')
      if (!payload.order_dir) throw new Error('排序类筛选必须选择 order_dir')
    }

    if (editingId.value) {
      await updateOpsPokemonFilterOption(editingId.value, payload)
      showOpsToast('筛选项已更新', 'success')
    } else {
      await createOpsPokemonFilterOption(payload)
      showOpsToast('筛选项已创建', 'success')
    }
    resetForm()
    closeDrawer()
    await loadData()
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || '保存失败'
    showOpsToast(error.value, 'error')
  } finally {
    saving.value = false
  }
}

async function removeItem(item: OpsPokemonFilterOptionItem) {
  if (!window.confirm(`确定删除筛选项 “${item.label}” 吗？`)) return
  try {
    await deleteOpsPokemonFilterOption(item.id)
    if (editingId.value === item.id) resetForm()
    await loadData()
    showOpsToast('筛选项已删除', 'success')
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '删除失败'
    showOpsToast(error.value, 'error')
  }
}

async function toggleActive(item: OpsPokemonFilterOptionItem) {
  try {
    await updateOpsPokemonFilterOption(item.id, {
      code: item.code,
      label: item.label,
      filter_type: item.filter_type,
      order_by: item.order_by,
      order_dir: item.order_dir,
      sort_order: item.sort_order,
      is_active: !item.is_active,
    })
    showOpsToast(item.is_active ? '已停用' : '已启用', 'success')
    await loadData()
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '操作失败'
    showOpsToast(error.value, 'error')
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
          <span class="query-label">关键字</span>
          <input
            v-model="keyword"
            type="text"
            placeholder="按 code / label 模糊搜索"
            @keyup.enter="search"
          />
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
        <span>请调整筛选条件或新增筛选项。</span>
      </div>
      <div v-else class="table-wrap">
        <table class="dict-table">
          <thead>
            <tr>
              <th class="col-index">序号</th>
              <th>code</th>
              <th>label</th>
              <th class="col-type">类型</th>
              <th>排序字段</th>
              <th class="col-dir">方向</th>
              <th class="col-sort">显示排序</th>
              <th class="col-status">状态</th>
              <th class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td class="mono-cell">{{ item.code }}</td>
              <td class="name-cell">{{ item.label }}</td>
              <td>{{ FILTER_TYPE_LABELS[item.filter_type] || item.filter_type }}</td>
              <td>{{ describeOrderBy(item.order_by) }}</td>
              <td>{{ describeOrderDir(item.order_dir) }}</td>
              <td>{{ item.sort_order }}</td>
              <td>
                <span class="badge" :class="item.is_active ? 'badge-on' : 'badge-off'">
                  {{ item.is_active ? '启用' : '停用' }}
                </span>
              </td>
              <td>
                <div class="action-group">
                  <button type="button" class="text-btn" @click="editItem(item)">修改</button>
                  <button type="button" class="text-btn" @click="toggleActive(item)">
                    {{ item.is_active ? '停用' : '启用' }}
                  </button>
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
          <button type="button" class="pager-btn" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">
            上一页
          </button>
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
          >
            下一页
          </button>
          <button type="button" class="pager-btn" :disabled="currentPage === totalPages" @click="goToPage(totalPages)">
            末页
          </button>
        </div>
      </div>
    </section>

    <div v-if="drawerVisible" class="modal-mask" @click="closeDrawer">
      <section class="dict-modal" @click.stop>
        <div class="modal-head">
          <div>
            <h2>{{ editingId ? '编辑筛选项' : '新增筛选项' }}</h2>
          </div>
          <button type="button" class="modal-close" @click="closeDrawer">关闭</button>
        </div>

        <form class="dict-form" @submit.prevent="submitForm">
          <div class="form-grid">
            <label class="form-row">
              <span>code</span>
              <input v-model="form.code" required type="text" placeholder="例如：total_desc" />
            </label>
            <label class="form-row">
              <span>label</span>
              <input v-model="form.label" required type="text" placeholder="例如：总种族值降序" />
            </label>
            <label class="form-row">
              <span>类型</span>
              <select v-model="form.filter_type" @change="onFilterTypeChange">
                <option value="shiny">shiny（异色筛选）</option>
                <option value="sort">sort（排序）</option>
              </select>
            </label>
            <label class="form-row">
              <span>显示排序</span>
              <input v-model="form.sort_order" type="number" placeholder="同类排序，越小越靠前" />
            </label>
            <label class="form-row" :class="{ disabled: !isSortType }">
              <span>排序字段</span>
              <select v-model="form.order_by" :disabled="!isSortType">
                <option v-for="opt in ORDER_BY_OPTIONS" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </label>
            <label class="form-row" :class="{ disabled: !isSortType }">
              <span>排序方向</span>
              <select v-model="form.order_dir" :disabled="!isSortType">
                <option value="">（不限）</option>
                <option value="asc">升序 asc</option>
                <option value="desc">降序 desc</option>
              </select>
            </label>
            <label class="form-row form-row-checkbox">
              <span>是否启用</span>
              <span class="checkbox-wrap">
                <input v-model="form.is_active" type="checkbox" />
                <span class="checkbox-text">启用后小程序图鉴页会展示该筛选项</span>
              </span>
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

.query-label,
.dict-form label span {
  color: #606266;
  font-size: 13px;
  white-space: nowrap;
}

.query-item input {
  width: 320px;
}

.query-actions {
  display: flex;
  align-items: center;
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
  font: inherit;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

input,
select {
  height: 36px;
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
  transition: border-color 0.15s ease, background-color 0.15s ease, color 0.15s ease;
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
  background: #fff;
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
  width: 70px;
}

.col-type,
.col-dir,
.col-sort,
.col-status {
  width: 100px;
}

.col-actions {
  width: 200px;
}

.mono-cell {
  font-family: 'Consolas', 'Menlo', 'Monaco', monospace;
  color: #606266;
  min-width: 160px;
}

.name-cell {
  min-width: 160px;
  font-weight: 600;
  color: #303133;
}

.action-group {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-width: 180px;
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

.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
}

.badge-on {
  background: #ecf5ff;
  color: #409eff;
  border: 1px solid #d9ecff;
}

.badge-off {
  background: #f4f4f5;
  color: #909399;
  border: 1px solid #e9e9eb;
}

.dict-form {
  display: grid;
  gap: 0;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px 20px;
}

.form-row {
  display: grid;
  grid-template-columns: 90px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
}

.form-row.disabled {
  opacity: 0.6;
}

.form-row-checkbox {
  grid-column: 1 / -1;
}

.checkbox-wrap {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.checkbox-wrap input {
  width: 16px;
  height: 16px;
  padding: 0;
}

.checkbox-text {
  color: #909399;
  font-size: 12px;
}

.form-row span {
  color: #606266;
  font-size: 13px;
}

.form-row input,
.form-row select {
  width: 100%;
}

.modal-footer {
  margin-top: 20px;
  padding-top: 4px;
}

.muted {
  color: var(--color-muted);
}

.error {
  color: #dc2626;
  background: #fef0f0;
  border: 1px solid #fde2e2;
  border-radius: 4px;
  padding: 10px 12px;
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
  padding: 0;
  display: grid;
  grid-template-rows: auto 1fr;
  overflow: hidden;
}

.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
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
  align-content: start;
  overflow: auto;
}

@media (max-width: 960px) {
  .query-item {
    width: 100%;
    flex-direction: column;
    align-items: flex-start;
  }

  .query-item input {
    width: 100%;
  }

  .query-actions {
    margin-left: 0;
  }

  .toolbar,
  .pagination {
    align-items: flex-start;
    flex-direction: column;
  }

  .pagination-controls {
    flex-wrap: wrap;
  }

  .form-row {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .dict-modal {
    width: 100%;
  }
}
</style>
