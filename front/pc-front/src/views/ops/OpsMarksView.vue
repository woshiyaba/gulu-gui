<script setup lang="ts">
import {computed, onMounted, reactive, ref} from 'vue'
import {
  clearOpsToken,
  createOpsMark,
  deleteOpsMark,
  fetchOpsMarks,
  fetchOpsMe,
  showOpsToast,
  updateOpsMark,
  type OpsMarkItem,
} from '@/api/ops'

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const keyword = ref('')
const items = ref<OpsMarkItem[]>([])
const isAdmin = ref(false)
const editingId = ref<number | null>(null)
const modalVisible = ref(false)
const currentPage = ref(1)
const pageSize = 10
const total = ref(0)

const form = reactive({
  key: '',
  zh_name: '',
  zh_description: '',
  image: '',
  sort_order: 0,
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const visiblePages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  for (let i = start; i <= end; i += 1) pages.push(i)
  return pages
})

function resetForm() {
  editingId.value = null
  form.key = ''
  form.zh_name = ''
  form.zh_description = ''
  form.image = ''
  form.sort_order = 0
}

function openCreateModal() {
  resetForm()
  modalVisible.value = true
}

function editItem(item: OpsMarkItem) {
  editingId.value = item.id
  form.key = item.key
  form.zh_name = item.zh_name
  form.zh_description = item.zh_description || ''
  form.image = item.image || ''
  form.sort_order = item.sort_order || 0
  modalVisible.value = true
}

function closeModal() {
  modalVisible.value = false
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [me, data] = await Promise.all([
      fetchOpsMe(),
      fetchOpsMarks({keyword: keyword.value.trim(), page: currentPage.value, page_size: pageSize}),
    ])
    isAdmin.value = me.role === 'admin'
    items.value = data.items
    total.value = data.total
    currentPage.value = data.page
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

async function goToPage(target: number) {
  if (target < 1 || target > totalPages.value || target === currentPage.value) return
  currentPage.value = target
  await loadData()
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

async function submit() {
  if (saving.value) return
  saving.value = true
  error.value = ''
  try {
    const payload = {
      key: form.key.trim(),
      zh_name: form.zh_name.trim(),
      zh_description: form.zh_description.trim(),
      image: form.image.trim(),
      sort_order: Number(form.sort_order) || 0,
    }
    if (editingId.value) {
      await updateOpsMark(editingId.value, payload)
      showOpsToast('印记已更新', 'success')
    } else {
      await createOpsMark(payload)
      showOpsToast('印记已创建', 'success')
    }
    closeModal()
    await loadData()
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '保存失败'
    showOpsToast(error.value, 'error')
  } finally {
    saving.value = false
  }
}

async function removeItem(item: OpsMarkItem) {
  if (!isAdmin.value) return
  if (!window.confirm(`确定删除印记「${item.zh_name}」吗？`)) return
  try {
    await deleteOpsMark(item.id)
    await loadData()
    showOpsToast('印记已删除', 'success')
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
          <span class="query-label">关键字</span>
          <input v-model="keyword" class="keyword-input" type="text" placeholder="英文标识 / 中文名"
                 @keyup.enter="search"/>
        </label>
        <div class="query-actions">
          <button type="button" class="btn-primary" @click="search">查询</button>
          <button type="button" class="btn-secondary" @click="resetFilters">重置</button>
        </div>
      </div>
    </section>

    <section class="table-card">
      <div class="toolbar">
        <button type="button" class="btn-primary" @click="openCreateModal">新增印记</button>
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
            <th>英文标识</th>
            <th>中文名</th>
            <th>说明</th>
            <th>排序</th>
            <th>操作</th>
          </tr>
          </thead>
          <tbody>
          <tr v-for="(item, index) in items" :key="item.id">
            <td>{{ (currentPage - 1) * pageSize + index + 1 }}</td>
            <td>{{ item.key }}</td>
            <td>{{ item.zh_name }}</td>
            <td class="desc-cell" :title="item.zh_description || ''">
              <span class="desc-text">{{ item.zh_description || '—' }}</span>
            </td>
            <td>{{ item.sort_order }}</td>
            <td>
              <button type="button" class="txt-btn" @click="editItem(item)">修改</button>
              <button v-if="isAdmin" type="button" class="txt-btn danger" @click="removeItem(item)">删除</button>
            </td>
          </tr>
          </tbody>
        </table>
      </div>

      <div v-if="total > 0" class="pager">
        <div class="pager-controls">
          <button type="button" class="pager-btn" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">
            上一页
          </button>
          <button
              v-for="p in visiblePages"
              :key="p"
              type="button"
              class="pager-btn"
              :class="{ active: p === currentPage }"
              @click="goToPage(p)"
          >
            {{ p }}
          </button>
          <button type="button" class="pager-btn" :disabled="currentPage === totalPages"
                  @click="goToPage(currentPage + 1)">下一页
          </button>
        </div>
      </div>
    </section>

    <div v-if="modalVisible" class="modal-mask">
      <section class="modal" @click.stop>
        <div class="modal-head">
          <h3>{{ editingId ? '编辑印记' : '新增印记' }}</h3>
        </div>
        <form class="modal-body" @submit.prevent="submit">
          <label>
            <span>英文标识</span>
            <input v-model="form.key" required maxlength="50" placeholder="例如 Slow Mark"/>
          </label>
          <label>
            <span>中文名</span>
            <input v-model="form.zh_name" required maxlength="50" placeholder="例如 减速印记"/>
          </label>
          <label>
            <span>排序</span>
            <input v-model.number="form.sort_order" type="number"/>
          </label>
          <label>
            <span>图片（可选）</span>
            <input v-model="form.image" placeholder="图片路径"/>
          </label>
          <label>
            <span>说明</span>
            <textarea v-model="form.zh_description" rows="4" placeholder="请输入说明"/>
          </label>

          <div class="actions">
            <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
            <button type="button" class="btn-secondary" @click="closeModal">取消</button>
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

.query-card, .table-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 16px;
}

.query-row {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.query-item {
  display: flex;
  gap: 8px;
  align-items: center;
}

.query-label {
  color: #606266;
  font-size: 13px;
}

.keyword-input {
  width: 240px;
  height: 36px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 0 12px;
}

.query-actions {
  display: flex;
  gap: 8px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.toolbar-meta {
  color: #909399;
  font-size: 13px;
}

.table-wrap {
  overflow: auto;
  border: 1px solid #ebeef5;
  border-radius: 2px;
}

.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.tbl th, .tbl td {
  border: 1px solid #ebeef5;
  padding: 10px;
  text-align: center;
}

.desc-cell {
  text-align: left;
  width: 360px;
  max-width: 360px;
}

.desc-text {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.placeholder {
  min-height: 120px;
  display: grid;
  place-items: center;
  color: #909399;
  border: 1px dashed #dcdfe6;
  border-radius: 2px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.pager-controls {
  display: flex;
  gap: 8px;
}

.pager-btn {
  min-width: 36px;
  height: 32px;
  border: 1px solid #dcdfe6;
  background: #fff;
  border-radius: 2px;
  cursor: pointer;
}

.pager-btn.active {
  background: #409eff;
  color: #fff;
  border-color: #409eff;
}

.pager-btn:disabled {
  color: #c0c4cc;
  border-color: #ebeef5;
  cursor: not-allowed;
}

.txt-btn {
  border: none;
  background: transparent;
  color: #409eff;
  cursor: pointer;
  margin: 0 4px;
}

.txt-btn.danger {
  color: #f56c6c;
}

.btn-primary, .btn-secondary {
  height: 36px;
  border-radius: 4px;
  padding: 0 14px;
  cursor: pointer;
}

.btn-primary {
  border: 1px solid #409eff;
  background: #409eff;
  color: #fff;
}

.btn-secondary {
  border: 1px solid #dcdfe6;
  background: #fff;
  color: #606266;
}

.error {
  color: #fff;
  background: #f56c6c;
  border: 1px solid #f56c6c;
  border-radius: 4px;
  padding: 10px 12px;
  margin-bottom: 10px;
}

.modal-mask {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.36);
  padding: 24px;
  z-index: 1000;
}

.modal {
  width: min(100%, 680px);
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.modal-head {
  padding: 16px 20px;
  border-bottom: 1px solid #ebeef5;
}

.modal-body {
  display: grid;
  gap: 10px;
  padding: 16px 20px 20px;
}

.modal-body label {
  display: grid;
  gap: 6px;
}

.modal-body span {
  color: #606266;
  font-size: 13px;
}

.modal-body input, .modal-body textarea {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 8px 10px;
  font-size: 13px;
}

.actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 8px;
}
</style>
