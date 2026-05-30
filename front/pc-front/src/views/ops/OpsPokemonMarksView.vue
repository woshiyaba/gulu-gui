<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  clearOpsToken,
  createOpsPokemonMark,
  deleteOpsPokemonMark,
  fetchOpsMe,
  fetchOpsPokemonMarks,
  showOpsToast,
  updateOpsPokemonMark,
  type OpsPokemonMarkItem,
} from '@/api/ops'

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const keyword = ref('')
const items = ref<OpsPokemonMarkItem[]>([])
const editingId = ref<number | null>(null)
const drawerVisible = ref(false)
const currentPage = ref(1)
const pageSize = 10
const total = ref(0)
const isAdmin = ref(false)

const form = reactive({
  key: '',
  zh_name: '',
  zh_description: '',
  sort_order: 0,
  image: '',
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

async function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  await loadData()
}

function resetForm() {
  editingId.value = null
  form.key = ''
  form.zh_name = ''
  form.zh_description = ''
  form.sort_order = 0
  form.image = ''
}

function openCreateDrawer() {
  resetForm()
  drawerVisible.value = true
}

function closeDrawer() {
  drawerVisible.value = false
}

function editItem(item: OpsPokemonMarkItem) {
  editingId.value = item.id
  form.key = item.key
  form.zh_name = item.zh_name
  form.zh_description = item.zh_description
  form.sort_order = item.sort_order
  form.image = item.image
  drawerVisible.value = true
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [me, marks] = await Promise.all([
      fetchOpsMe(),
      fetchOpsPokemonMarks({
        keyword: keyword.value.trim() || undefined,
        page: currentPage.value,
        page_size: pageSize,
      }),
    ])
    isAdmin.value = me.role === 'admin'
    items.value = marks.items
    total.value = marks.total
    currentPage.value = marks.page
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
  keyword.value = ''
  currentPage.value = 1
  await loadData()
}

async function submitForm() {
  if (saving.value) return
  saving.value = true
  error.value = ''
  try {
    const payload = {
      key: form.key.trim(),
      zh_name: form.zh_name.trim(),
      zh_description: form.zh_description.trim(),
      sort_order: Number(form.sort_order) || 0,
      image: form.image.trim(),
    }
    if (editingId.value) {
      await updateOpsPokemonMark(editingId.value, payload)
      showOpsToast('词条已更新', 'success')
    } else {
      await createOpsPokemonMark(payload)
      showOpsToast('词条已创建', 'success')
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

async function removeItem(item: OpsPokemonMarkItem) {
  if (!window.confirm(`确定删除"${item.zh_name}"吗？`)) return
  try {
    await deleteOpsPokemonMark(item.id)
    if (editingId.value === item.id) resetForm()
    await loadData()
    showOpsToast('词条已删除', 'success')
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
      <div class="ops-filter-bar" style="align-items:flex-end;margin-bottom:16px;">
        <label class="ops-form-item" style="min-width:180px;">
          <span class="ops-filter-label">关键字</span>
          <input v-model="keyword" class="ops-input" type="text" placeholder="按中文名或英文 key 模糊搜索" @keyup.enter="search" />
        </label>
        <div class="ops-filter-actions">
          <button type="button" class="ops-btn ops-btn-primary" @click="search">搜索</button>
          <button type="button" class="ops-btn ops-btn-secondary" @click="resetFilters">重置</button>
        </div>
      </div>
      <div class="ops-toolbar">
        <button type="button" class="ops-btn ops-btn-primary" @click="openCreateDrawer">新增</button>
        <span class="ops-toolbar-meta">共 {{ total }} 条</span>
      </div>

      <p v-if="error" class="ops-error">{{ error }}</p>

      <div v-if="loading" class="ops-loading">加载中...</div>
      <div v-else-if="!items.length" class="ops-empty">
        <strong>暂无数据</strong>
        <span>请调整筛选条件或新增词条。</span>
      </div>
      <div v-else class="ops-table-wrap">
        <table class="ops-table">
          <thead>
            <tr>
              <th class="ops-col-index">序号</th>
              <th style="width:70px;">图标</th>
              <th>英文标识</th>
              <th>中文名</th>
              <th>中文描述</th>
              <th class="ops-col-sort">排序</th>
              <th class="ops-col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td>
                <img
                  v-if="item.image_url"
                  :src="item.image_url"
                  :alt="item.zh_name"
                  style="width:40px;height:40px;object-fit:contain;border-radius:4px;border:1px solid var(--ops-border);background:var(--ops-bg);"
                  loading="lazy"
                />
                <span v-else style="color:var(--ops-muted);">-</span>
              </td>
              <td style="font-family:Consolas,Menlo,monospace;color:var(--ops-text-secondary);min-width:160px;">{{ item.key }}</td>
              <td style="min-width:140px;font-weight:600;">{{ item.zh_name }}</td>
              <td style="max-width:420px;min-width:260px;text-align:left;line-height:1.7;white-space:pre-wrap;word-break:break-word;">{{ item.zh_description || '-' }}</td>
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
        <span class="ops-pagination-summary">共 {{ total }} 条，当前显示 {{ pageStart }}-{{ pageEnd }} 条</span>
        <div class="ops-pagination-controls">
          <button type="button" class="ops-page-btn" :disabled="currentPage === 1" @click="goToPage(1)">首页</button>
          <button type="button" class="ops-page-btn" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">上一页</button>
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
          <button type="button" class="ops-page-btn" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">下一页</button>
          <button type="button" class="ops-page-btn" :disabled="currentPage === totalPages" @click="goToPage(totalPages)">末页</button>
        </div>
      </div>
    </section>

    <div v-if="drawerVisible" class="ops-modal-mask">
      <section class="ops-modal" @click.stop>
        <div class="ops-modal-header">
          <h3>{{ editingId ? '编辑词条' : '新增词条' }}</h3>
          <button type="button" class="ops-modal-close" @click="closeDrawer">✕</button>
        </div>

        <form class="ops-modal-body" @submit.prevent="submitForm">
          <div class="ops-form-grid">
            <label class="ops-form-row">
              <span>英文标识</span>
              <input v-model="form.key" class="ops-input" required type="text" placeholder="例如：Poison Mark" />
            </label>
            <label class="ops-form-row">
              <span>中文名</span>
              <input v-model="form.zh_name" class="ops-input" required type="text" placeholder="例如：中毒印记" />
            </label>
            <label class="ops-form-row">
              <span>显示排序</span>
              <input v-model="form.sort_order" class="ops-input" type="number" placeholder="同类排序唯一" />
            </label>
            <label class="ops-form-row">
              <span>图标路径</span>
              <input v-model="form.image" class="ops-input" type="text" placeholder="可选，静态资源相对路径" />
            </label>
            <label class="ops-form-row ops-form-grid-full" style="align-items:start;">
              <span>中文描述</span>
              <textarea v-model="form.zh_description" class="ops-input" style="height:auto;min-height:120px;padding:10px 14px;resize:vertical;" rows="5" placeholder="词条的详细说明，支持换行"></textarea>
            </label>
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
