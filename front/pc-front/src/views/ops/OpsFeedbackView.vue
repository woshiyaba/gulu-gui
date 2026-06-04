<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  clearOpsToken,
  fetchOpsFeedback,
  showOpsToast,
  updateOpsFeedbackStatus,
  type OpsFeedbackItem,
} from '@/api/ops'

const loading = ref(false)
const error = ref('')
const items = ref<OpsFeedbackItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const updatingId = ref<number | null>(null)
const detailVisible = ref(false)
const detailItem = ref<OpsFeedbackItem | null>(null)

const filters = reactive({
  status: '',
})

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'pending', label: '待处理' },
  { value: 'handled', label: '已处理' },
]

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

function formatDate(value: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (num: number) => String(num).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function statusLabel(status: string) {
  if (status === 'handled') return '已处理'
  if (status === 'pending') return '待处理'
  return status
}

function openDetail(item: OpsFeedbackItem) {
  detailItem.value = item
  detailVisible.value = true
}

function closeDetail() {
  detailVisible.value = false
  detailItem.value = null
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const result = await fetchOpsFeedback({
      status: filters.status || undefined,
      limit: pageSize,
      offset: (currentPage.value - 1) * pageSize,
    })
    items.value = result.items
    total.value = result.total
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
  filters.status = ''
  currentPage.value = 1
  await loadData()
}

async function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  await loadData()
}

async function toggleStatus(item: OpsFeedbackItem) {
  if (updatingId.value !== null) return
  const next = item.status === 'handled' ? 'pending' : 'handled'
  updatingId.value = item.id
  try {
    const updated = await updateOpsFeedbackStatus(item.id, next)
    item.status = updated.status
    item.updated_at = updated.updated_at
    if (detailItem.value && detailItem.value.id === item.id) {
      detailItem.value = { ...detailItem.value, status: updated.status, updated_at: updated.updated_at }
    }
    showOpsToast(next === 'handled' ? '已标记为已处理' : '已恢复为待处理', 'success')
  } catch (err: any) {
    if (err?.response?.status === 401) {
      clearOpsToken()
      return
    }
    showOpsToast(err?.response?.data?.detail || '更新失败', 'error')
  } finally {
    updatingId.value = null
  }
}

onMounted(() => {
  void loadData()
})
</script>

<template>
  <div class="ops-page">
    <section class="ops-card-padded">
      <div class="ops-filter-bar" style="align-items:flex-end;flex-wrap:wrap;margin-bottom:16px;">
        <label class="ops-form-item" style="min-width:160px;">
          <span class="ops-filter-label">处理状态</span>
          <select v-model="filters.status" class="ops-select">
            <option v-for="option in statusOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
        <div class="ops-filter-actions">
          <button type="button" class="ops-btn ops-btn-primary" @click="search">搜索</button>
          <button type="button" class="ops-btn ops-btn-secondary" @click="resetFilters">重置</button>
        </div>
      </div>
      <div class="ops-toolbar">
        <span class="ops-section-title">用户反馈</span>
        <span class="ops-toolbar-meta">共 {{ total }} 条</span>
      </div>

      <p v-if="error" class="ops-error">{{ error }}</p>
      <div v-if="loading" class="ops-loading">加载中...</div>
      <div v-else-if="!items.length" class="ops-empty">暂无反馈</div>

      <div v-else class="ops-table-wrap">
        <table class="ops-table" style="min-width:920px;">
          <thead>
            <tr>
              <th style="width:72px;">序号</th>
              <th>提交时间</th>
              <th style="width:100px;">类型</th>
              <th>反馈内容</th>
              <th style="width:160px;">联系方式</th>
              <th style="width:100px;">用户 id</th>
              <th style="width:90px;">状态</th>
              <th style="width:170px;">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td>{{ formatDate(item.created_at) }}</td>
              <td>
                <span v-if="item.feedback_type" class="ops-badge ops-badge--default">{{ item.feedback_type }}</span>
                <span v-else style="color:var(--ops-muted);">-</span>
              </td>
              <td style="max-width:360px;">
                <div style="display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;line-height:1.5;">
                  {{ item.content }}
                </div>
              </td>
              <td>{{ item.contact || '-' }}</td>
              <td>{{ item.user_id ?? '匿名' }}</td>
              <td>
                <span class="ops-badge" :class="item.status === 'handled' ? 'ops-badge--success' : 'ops-badge--warning'">
                  {{ statusLabel(item.status) }}
                </span>
              </td>
              <td>
                <button type="button" class="ops-btn ops-btn-text" @click="openDetail(item)">查看</button>
                <button
                  type="button"
                  class="ops-btn ops-btn-text"
                  :disabled="updatingId === item.id"
                  @click="toggleStatus(item)"
                >
                  {{ item.status === 'handled' ? '设为待处理' : '设为已处理' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="total > 0" class="ops-pagination">
        <span class="ops-pagination-summary">第 {{ pageStart }}-{{ pageEnd }} 条 / 共 {{ total }} 条</span>
        <div class="ops-pagination-controls">
          <button type="button" class="ops-page-btn" :disabled="currentPage <= 1" @click="goToPage(currentPage - 1)">上一页</button>
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
          <button type="button" class="ops-page-btn" :disabled="currentPage >= totalPages" @click="goToPage(currentPage + 1)">下一页</button>
        </div>
      </div>
    </section>

    <div v-if="detailVisible && detailItem" class="ops-modal-mask" @click.self="closeDetail">
      <section class="ops-modal" @click.stop>
        <div class="ops-modal-header">
          <div>
            <h3>反馈详情 #{{ detailItem.id }}</h3>
            <p style="margin:4px 0 0;color:var(--ops-muted);font-size:13px;">
              {{ formatDate(detailItem.created_at) }} ·
              {{ detailItem.feedback_type || '未分类' }} ·
              {{ statusLabel(detailItem.status) }}
            </p>
          </div>
          <button type="button" class="ops-btn ops-btn-text" @click="closeDetail">关闭</button>
        </div>
        <div class="ops-modal-body">
          <div style="display:grid;gap:14px;">
            <div>
              <div style="color:var(--ops-text-secondary);font-size:13px;font-weight:600;margin-bottom:6px;">反馈内容</div>
              <div style="white-space:pre-wrap;word-break:break-word;line-height:1.7;padding:12px;border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);background:var(--ops-bg);">
                {{ detailItem.content }}
              </div>
            </div>
            <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:14px;">
              <div>
                <div style="color:var(--ops-text-secondary);font-size:13px;font-weight:600;margin-bottom:6px;">联系方式</div>
                <div>{{ detailItem.contact || '未填写' }}</div>
              </div>
              <div>
                <div style="color:var(--ops-text-secondary);font-size:13px;font-weight:600;margin-bottom:6px;">用户 id</div>
                <div>{{ detailItem.user_id ?? '匿名' }}</div>
              </div>
            </div>
          </div>
        </div>
        <div class="ops-modal-footer" style="display:flex;justify-content:flex-end;gap:10px;">
          <button
            type="button"
            class="ops-btn ops-btn-primary"
            :disabled="updatingId === detailItem.id"
            @click="toggleStatus(detailItem)"
          >
            {{ detailItem.status === 'handled' ? '设为待处理' : '设为已处理' }}
          </button>
          <button type="button" class="ops-btn ops-btn-secondary" @click="closeDetail">关闭</button>
        </div>
      </section>
    </div>
  </div>
</template>
