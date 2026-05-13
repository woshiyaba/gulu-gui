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
    <section class="ops-card-padded">
      <div class="ops-filter-bar" style="margin-bottom:16px;">
        <div class="ops-filter-item">
          <span class="ops-filter-label">关键字</span>
          <input v-model="keyword" class="ops-input" style="width:240px" type="text" placeholder="英文标识 / 中文名" @keyup.enter="search" />
        </div>
        <div class="ops-filter-actions">
          <button type="button" class="ops-btn ops-btn-primary" @click="search">查询</button>
          <button type="button" class="ops-btn ops-btn-secondary" @click="resetFilters">重置</button>
        </div>
      </div>
      <div class="ops-toolbar">
        <button type="button" class="ops-btn ops-btn-primary" @click="openCreateModal">新增印记</button>
        <span class="ops-toolbar-meta">共 {{ total }} 条</span>
      </div>

      <p v-if="error" class="ops-error">{{ error }}</p>
      <div v-if="loading" class="ops-loading">加载中...</div>
      <div v-else-if="!items.length" class="ops-empty"><strong>暂无数据</strong></div>
      <div v-else class="ops-table-wrap">
        <table class="ops-table">
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
              <td style="max-width:360px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" :title="item.zh_description || ''">{{ item.zh_description || '—' }}</td>
              <td>{{ item.sort_order }}</td>
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
        <div class="ops-pagination-controls">
          <button type="button" class="ops-page-btn" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">上一页</button>
          <button v-for="p in visiblePages" :key="p" type="button" class="ops-page-btn" :class="{ 'ops-page-btn--active': p === currentPage }" @click="goToPage(p)">{{ p }}</button>
          <button type="button" class="ops-page-btn" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">下一页</button>
        </div>
      </div>
    </section>

    <div v-if="modalVisible" class="ops-modal-mask">
      <section class="ops-modal" @click.stop>
        <div class="ops-modal-header">
          <h3>{{ editingId ? '编辑印记' : '新增印记' }}</h3>
          <button type="button" class="ops-modal-close" @click="closeModal">✕</button>
        </div>
        <form class="ops-modal-body" @submit.prevent="submit">
          <div style="display:grid;gap:12px;">
            <div class="ops-form-item">
              <label>英文标识</label>
              <input v-model="form.key" class="ops-input" required maxlength="50" placeholder="例如 Slow Mark" />
            </div>
            <div class="ops-form-item">
              <label>中文名</label>
              <input v-model="form.zh_name" class="ops-input" required maxlength="50" placeholder="例如 减速印记" />
            </div>
            <div class="ops-form-item">
              <label>排序</label>
              <input v-model.number="form.sort_order" class="ops-input" type="number" />
            </div>
            <div class="ops-form-item">
              <label>图片（可选）</label>
              <input v-model="form.image" class="ops-input" placeholder="图片路径" />
            </div>
            <div class="ops-form-item">
              <label>说明</label>
              <textarea v-model="form.zh_description" class="ops-input" style="height:auto;min-height:72px;padding:8px 12px;resize:vertical;" rows="4" placeholder="请输入说明" />
            </div>
          </div>
          <div class="ops-modal-footer">
            <button type="submit" class="ops-btn ops-btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
            <button type="button" class="ops-btn ops-btn-secondary" @click="closeModal">取消</button>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>
