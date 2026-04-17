<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  clearOpsToken,
  createOpsDict,
  deleteOpsDict,
  fetchOpsDicts,
  fetchOpsMe,
  showOpsToast,
  updateOpsDict,
  type OpsDictItem,
} from '@/api/ops'

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const dictType = ref('')
const dictCode = ref('')
const dictLabel = ref('')
const items = ref<OpsDictItem[]>([])
const editingId = ref<number | null>(null)
const drawerVisible = ref(false)
const currentPage = ref(1)
const pageSize = 10
const total = ref(0)

const form = reactive({
  dict_type: '',
  code: '',
  label: '',
  sort_order: 0,
})

const isAdmin = ref(false)
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

async function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  await loadData()
}

function resetForm() {
  editingId.value = null
  form.dict_type = ''
  form.code = ''
  form.label = ''
  form.sort_order = 0
}

function openCreateDrawer() {
  resetForm()
  drawerVisible.value = true
}

function closeDrawer() {
  drawerVisible.value = false
}

function editItem(item: OpsDictItem) {
  editingId.value = item.id
  form.dict_type = item.dict_type
  form.code = item.code
  form.label = item.label
  form.sort_order = item.sort_order
  drawerVisible.value = true
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [me, dicts] = await Promise.all([
      fetchOpsMe(),
      fetchOpsDicts({
        dict_type: dictType.value.trim() || undefined,
        code: dictCode.value.trim() || undefined,
        label: dictLabel.value.trim() || undefined,
        page: currentPage.value,
        page_size: pageSize,
      }),
    ])
    isAdmin.value = me.role === 'admin'
    items.value = dicts.items
    total.value = dicts.total
    currentPage.value = dicts.page
  } catch (err: any) {
    const detail = err?.response?.data?.detail || '加载失败'
    if (err?.response?.status === 401) {
      clearOpsToken()
      return
    }
    error.value = detail
  } finally {
    loading.value = false
  }
}

async function search() {
  currentPage.value = 1
  await loadData()
}

async function resetFilters() {
  dictType.value = ''
  dictCode.value = ''
  dictLabel.value = ''
  currentPage.value = 1
  await loadData()
}

async function submitForm() {
  if (saving.value) return
  saving.value = true
  error.value = ''
  try {
    const payload = {
      dict_type: form.dict_type.trim(),
      code: form.code.trim(),
      label: form.label.trim(),
      sort_order: Number(form.sort_order) || 0,
    }
    if (editingId.value) {
      await updateOpsDict(editingId.value, payload)
      showOpsToast('字典项已更新', 'success')
    } else {
      await createOpsDict(payload)
      showOpsToast('字典项已创建', 'success')
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

async function removeItem(item: OpsDictItem) {
  if (!isAdmin.value) return
  if (!window.confirm(`确定删除 ${item.dict_type} / ${item.label} 吗？`)) return
  try {
    await deleteOpsDict(item.id)
    if (editingId.value === item.id) resetForm()
    await loadData()
    showOpsToast('字典项已删除', 'success')
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
    <section class="query-card">
      <div class="query-row">
        <label class="query-item">
          <span class="query-label">字典类型</span>
          <input v-model="dictType" type="text" placeholder="请输入字典类型" />
        </label>
        <label class="query-item">
          <span class="query-label">字典编码</span>
          <input v-model="dictCode" type="text" placeholder="请输入字典编码" />
        </label>
        <label class="query-item">
          <span class="query-label">字典名称</span>
          <input v-model="dictLabel" type="text" placeholder="请输入字典名称" />
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
        <span>请调整筛选条件后重试，或新增字典项。</span>
      </div>
      <div v-else class="table-wrap">
        <table class="dict-table">
          <thead>
            <tr>
              <th class="col-index">序号</th>
              <th>字典类型</th>
              <th>字典编码</th>
              <th>字典名称</th>
              <th class="col-sort">排序</th>
              <th class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td>{{ item.dict_type }}</td>
              <td>{{ item.code }}</td>
              <td class="label-cell">{{ item.label }}</td>
              <td>{{ item.sort_order }}</td>
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
            <h2>{{ editingId ? '编辑字典项' : '新增字典项' }}</h2>
          </div>
          <button type="button" class="modal-close" @click="closeDrawer">关闭</button>
        </div>

        <form class="dict-form" @submit.prevent="submitForm">
          <div class="form-grid">
            <label class="form-row">
              <span>字典类型</span>
              <input v-model="form.dict_type" required type="text" placeholder="请输入字典类型" />
            </label>
            <label class="form-row">
              <span>字典编码</span>
              <input v-model="form.code" required type="text" placeholder="请输入字典编码" />
            </label>
            <label class="form-row">
              <span>字典名称</span>
              <input v-model="form.label" required type="text" placeholder="请输入字典名称" />
            </label>
            <label class="form-row">
              <span>显示排序</span>
              <input v-model="form.sort_order" type="number" placeholder="请输入排序" />
            </label>
          </div>
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
  width: 260px;
}

.query-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: 12px;
}

input {
  height: 36px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #fff;
  color: #303133;
  padding: 0 14px;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

input:focus {
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
  width: 90px;
}

.col-sort {
  width: 90px;
}

.col-actions {
  width: 160px;
}

.label-cell {
  min-width: 180px;
  text-align: center;
}

.action-group {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  min-width: 120px;
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
  gap: 0;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px 20px;
}

.form-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
}

.form-row span {
  color: #606266;
  font-size: 13px;
}

.form-row input {
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
  width: min(100%, 640px);
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
