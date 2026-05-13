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
  if (!window.confirm(`确定删除筛选项 "${item.label}" 吗？`)) return
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
    <section class="ops-card-padded">
      <div class="ops-filter-bar" style="margin-bottom:16px;">
        <div class="ops-filter-item">
          <span class="ops-filter-label">关键字</span>
          <input v-model="keyword" class="ops-input" style="width:320px" type="text" placeholder="按 code / label 模糊搜索" @keyup.enter="search" />
        </div>
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
      <div v-else-if="!items.length" class="ops-empty"><strong>暂无数据</strong><span>请调整筛选条件或新增筛选项。</span></div>
      <div v-else class="ops-table-wrap">
        <table class="ops-table">
          <thead>
            <tr>
              <th>序号</th>
              <th>code</th>
              <th>label</th>
              <th>类型</th>
              <th>排序字段</th>
              <th>方向</th>
              <th>显示排序</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td><code>{{ item.code }}</code></td>
              <td style="font-weight:500;">{{ item.label }}</td>
              <td>{{ FILTER_TYPE_LABELS[item.filter_type] || item.filter_type }}</td>
              <td>{{ describeOrderBy(item.order_by) }}</td>
              <td>{{ describeOrderDir(item.order_dir) }}</td>
              <td>{{ item.sort_order }}</td>
              <td><span class="ops-badge" :class="item.is_active ? 'ops-badge--accent' : 'ops-badge--default'">{{ item.is_active ? '启用' : '停用' }}</span></td>
              <td>
                <div class="ops-action-group">
                  <button type="button" class="ops-btn ops-btn-text" @click="editItem(item)">修改</button>
                  <button type="button" class="ops-btn ops-btn-text" @click="toggleActive(item)">{{ item.is_active ? '停用' : '启用' }}</button>
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
          <button v-for="page in visiblePages" :key="page" type="button" class="ops-page-btn" :class="{ 'ops-page-btn--active': page === currentPage }" @click="goToPage(page)">{{ page }}</button>
          <button type="button" class="ops-page-btn" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">下一页</button>
          <button type="button" class="ops-page-btn" :disabled="currentPage === totalPages" @click="goToPage(totalPages)">末页</button>
        </div>
      </div>
    </section>

    <div v-if="drawerVisible" class="ops-modal-mask" @click="closeDrawer">
      <section class="ops-modal" @click.stop>
        <div class="ops-modal-header">
          <h3>{{ editingId ? '编辑筛选项' : '新增筛选项' }}</h3>
          <button type="button" class="ops-modal-close" @click="closeDrawer">✕</button>
        </div>
        <form class="ops-modal-body" @submit.prevent="submitForm">
          <div class="ops-form-grid">
            <div class="ops-form-item">
              <label>code</label>
              <input v-model="form.code" class="ops-input" required type="text" placeholder="例如：total_desc" />
            </div>
            <div class="ops-form-item">
              <label>label</label>
              <input v-model="form.label" class="ops-input" required type="text" placeholder="例如：总种族值降序" />
            </div>
            <div class="ops-form-item">
              <label>类型</label>
              <select v-model="form.filter_type" class="ops-select" @change="onFilterTypeChange">
                <option value="shiny">shiny（异色筛选）</option>
                <option value="sort">sort（排序）</option>
              </select>
            </div>
            <div class="ops-form-item">
              <label>显示排序</label>
              <input v-model="form.sort_order" class="ops-input" type="number" placeholder="越小越靠前" />
            </div>
            <div class="ops-form-item" :style="{ opacity: isSortType ? 1 : 0.6 }">
              <label>排序字段</label>
              <select v-model="form.order_by" class="ops-select" :disabled="!isSortType">
                <option v-for="opt in ORDER_BY_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>
            <div class="ops-form-item" :style="{ opacity: isSortType ? 1 : 0.6 }">
              <label>排序方向</label>
              <select v-model="form.order_dir" class="ops-select" :disabled="!isSortType">
                <option value="">（不限）</option>
                <option value="asc">升序 asc</option>
                <option value="desc">降序 desc</option>
              </select>
            </div>
            <div class="ops-form-item" style="grid-column:1/-1;">
              <label style="display:flex;align-items:center;gap:8px;">
                <input v-model="form.is_active" type="checkbox" style="width:16px;height:16px;" />
                <span style="color:var(--ops-text-secondary);font-size:12px;">启用后小程序图鉴页会展示该筛选项</span>
              </label>
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
