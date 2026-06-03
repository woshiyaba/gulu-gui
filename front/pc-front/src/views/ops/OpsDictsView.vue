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
  extra: '',
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
  form.extra = ''
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
  form.extra = item.extra
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
      extra: form.extra.trim(),
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
    <section class="ops-card-padded">
      <div class="ops-filter-bar" style="margin-bottom:16px;">
        <div class="ops-filter-item">
          <span class="ops-filter-label">字典类型</span>
          <input v-model="dictType" type="text" placeholder="请输入字典类型" class="ops-input" />
        </div>
        <div class="ops-filter-item">
          <span class="ops-filter-label">字典编码</span>
          <input v-model="dictCode" type="text" placeholder="请输入字典编码" class="ops-input" />
        </div>
        <div class="ops-filter-item">
          <span class="ops-filter-label">字典名称</span>
          <input v-model="dictLabel" type="text" placeholder="请输入字典名称" class="ops-input" />
        </div>
        <div class="ops-filter-actions">
          <button type="button" class="ops-btn ops-btn-primary" @click="search">搜索</button>
          <button type="button" class="ops-btn ops-btn-secondary" @click="resetFilters">重置</button>
        </div>
      </div>
      <div class="ops-toolbar">
        <button type="button" class="ops-btn ops-btn-primary" @click="openCreateDrawer">新增</button>
        <div class="ops-toolbar-meta">共 {{ total }} 条</div>
      </div>

      <p v-if="error" class="ops-alert ops-alert--error">{{ error }}</p>

      <div v-if="loading" class="ops-loading">加载中...</div>
      <div v-else-if="!items.length" class="ops-empty">
        <strong>暂无数据</strong>
        <span>请调整筛选条件后重试，或新增字典项。</span>
      </div>
      <div v-else class="ops-table-wrap">
        <table class="ops-table">
          <thead>
            <tr>
              <th class="ops-col-index">序号</th>
              <th>字典类型</th>
              <th>字典编码</th>
              <th>字典名称</th>
              <th>扩展信息</th>
              <th class="ops-col-sort">排序</th>
              <th class="ops-col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td>{{ item.dict_type }}</td>
              <td>{{ item.code }}</td>
              <td>{{ item.label }}</td>
              <td>{{ item.extra || '-' }}</td>
              <td>{{ item.sort_order }}</td>
              <td>
                <div class="ops-action-group">
                  <button type="button" class="ops-btn ops-btn-text" @click="editItem(item)">修改</button>
                  <button type="button" class="ops-btn ops-btn-text ops-btn--danger" @click="removeItem(item)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="total > 0" class="ops-pagination">
        <div class="ops-pagination-summary">
          共 {{ total }} 条，当前显示 {{ pageStart }}-{{ pageEnd }} 条
        </div>
        <div class="ops-pagination-controls">
          <button type="button" class="ops-page-btn" :disabled="currentPage === 1" @click="goToPage(1)">首页</button>
          <button type="button" class="ops-page-btn" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">
            上一页
          </button>
          <button
            v-for="page in visiblePages"
            :key="page"
            type="button"
            class="ops-page-btn"
            :class="{ 'ops-page-btn--active': page === currentPage }"
            @click="goToPage(page)"
          >
            {{ page }}
          </button>
          <button
            type="button"
            class="ops-page-btn"
            :disabled="currentPage === totalPages"
            @click="goToPage(currentPage + 1)"
          >
            下一页
          </button>
          <button type="button" class="ops-page-btn" :disabled="currentPage === totalPages" @click="goToPage(totalPages)">
            末页
          </button>
        </div>
      </div>
    </section>

    <div v-if="drawerVisible" class="ops-modal-mask">
      <section class="ops-modal" @click.stop>
        <div class="ops-modal-header">
          <h3>{{ editingId ? '编辑字典项' : '新增字典项' }}</h3>
          <button type="button" class="ops-modal-close" @click="closeDrawer">✕</button>
        </div>

        <form @submit.prevent="submitForm">
          <div class="ops-modal-body">
            <div class="ops-form-grid">
              <div class="ops-form-item">
                <label>字典类型</label>
                <input v-model="form.dict_type" required type="text" placeholder="请输入字典类型" class="ops-input" />
              </div>
              <div class="ops-form-item">
                <label>字典编码</label>
                <input v-model="form.code" required type="text" placeholder="请输入字典编码" class="ops-input" />
              </div>
              <div class="ops-form-item">
                <label>字典名称</label>
                <textarea
                  v-model="form.label"
                  required
                  rows="3"
                  placeholder="请输入字典名称（按回车换行，将作为真实换行符保存）"
                  class="ops-input ops-textarea"
                />
              </div>
              <div class="ops-form-item">
                <label>扩展信息</label>
                <input v-model="form.extra" type="text" placeholder="可选，如 single/multi" class="ops-input" />
              </div>
              <div class="ops-form-item">
                <label>显示排序</label>
                <input v-model="form.sort_order" type="number" placeholder="请输入排序" class="ops-input" />
              </div>
            </div>
          </div>
          <div class="ops-modal-footer">
            <button type="submit" class="ops-btn ops-btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
            <button type="button" class="ops-btn ops-btn-secondary" @click="closeDrawer">取消</button>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>

<style scoped>
/* All styles replaced by global ops-design-system classes */
</style>
