<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { clearOpsToken, fetchOpsAuditLogs, type OpsAuditLogItem } from '@/api/ops'

type DiffStatus = 'added' | 'deleted' | 'changed'

interface DiffRow {
  path: string
  before: unknown
  after: unknown
  status: DiffStatus
}

const loading = ref(false)
const error = ref('')
const items = ref<OpsAuditLogItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const detailVisible = ref(false)
const detailItem = ref<OpsAuditLogItem | null>(null)

const filters = reactive({
  username: '',
  resource_type: '',
  resource_id: '',
  action: '',
})

const actionOptions = [
  { value: '', label: '全部动作' },
  { value: 'create', label: 'create' },
  { value: 'update', label: 'update' },
  { value: 'delete', label: 'delete' },
  { value: 'force_delete', label: 'force_delete' },
  { value: 'reset', label: 'reset' },
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

const detailDiffRows = computed(() => {
  if (!detailItem.value) return []
  return buildDiffRows(detailItem.value.before_json, detailItem.value.after_json)
})

function formatDate(value: string) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (num: number) => String(num).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function formatJson(value: Record<string, unknown> | null) {
  if (!value) return '无'
  return JSON.stringify(value, null, 2)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function flattenJson(value: unknown, prefix = ''): Map<string, unknown> {
  const result = new Map<string, unknown>()
  if (Array.isArray(value)) {
    if (!value.length && prefix) {
      result.set(prefix, value)
      return result
    }
    value.forEach((item, index) => {
      flattenJson(item, `${prefix}[${index}]`).forEach((childValue, childPath) => {
        result.set(childPath, childValue)
      })
    })
    return result
  }
  if (isRecord(value)) {
    const entries = Object.entries(value)
    if (!entries.length && prefix) {
      result.set(prefix, value)
      return result
    }
    entries.forEach(([key, childValue]) => {
      const nextPath = prefix ? `${prefix}.${key}` : key
      flattenJson(childValue, nextPath).forEach((leafValue, leafPath) => {
        result.set(leafPath, leafValue)
      })
    })
    return result
  }
  result.set(prefix || '(root)', value)
  return result
}

function stableValue(value: unknown) {
  return JSON.stringify(value)
}

function buildDiffRows(before: Record<string, unknown> | null, after: Record<string, unknown> | null): DiffRow[] {
  const beforeMap = flattenJson(before)
  const afterMap = flattenJson(after)
  const paths = Array.from(new Set([...beforeMap.keys(), ...afterMap.keys()])).sort()
  const rows: DiffRow[] = []
  paths.forEach((path) => {
    const hasBefore = beforeMap.has(path)
    const hasAfter = afterMap.has(path)
    const beforeValue = beforeMap.get(path)
    const afterValue = afterMap.get(path)
    if (!hasBefore && hasAfter) {
      rows.push({ path, before: undefined, after: afterValue, status: 'added' })
    } else if (hasBefore && !hasAfter) {
      rows.push({ path, before: beforeValue, after: undefined, status: 'deleted' })
    } else if (stableValue(beforeValue) !== stableValue(afterValue)) {
      rows.push({ path, before: beforeValue, after: afterValue, status: 'changed' })
    }
  })
  return rows
}

function formatDiffValue(value: unknown) {
  if (value === undefined) return '-'
  if (value === null) return 'null'
  if (typeof value === 'string') return value || '""'
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value)
}

function diffStatusLabel(status: DiffStatus) {
  if (status === 'added') return '新增'
  if (status === 'deleted') return '删除'
  return '变更'
}

function operatorName(item: OpsAuditLogItem) {
  return item.nickname || item.username || `用户 ${item.user_id}`
}

function openDetail(item: OpsAuditLogItem) {
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
    const result = await fetchOpsAuditLogs({
      username: filters.username.trim() || undefined,
      resource_type: filters.resource_type.trim() || undefined,
      resource_id: filters.resource_id.trim() || undefined,
      action: filters.action || undefined,
      page: currentPage.value,
      page_size: pageSize,
    })
    items.value = result.items
    total.value = result.total
    currentPage.value = result.page
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
  filters.username = ''
  filters.resource_type = ''
  filters.resource_id = ''
  filters.action = ''
  currentPage.value = 1
  await loadData()
}

async function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  await loadData()
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
          <span class="query-label">操作者</span>
          <input v-model="filters.username" type="text" placeholder="账号或昵称" @keyup.enter="search" />
        </label>
        <label class="query-item">
          <span class="query-label">资源类型</span>
          <input v-model="filters.resource_type" type="text" placeholder="如 pokemon / skill" @keyup.enter="search" />
        </label>
        <label class="query-item">
          <span class="query-label">资源 ID</span>
          <input v-model="filters.resource_id" type="text" placeholder="资源 ID" @keyup.enter="search" />
        </label>
        <label class="query-item">
          <span class="query-label">动作</span>
          <select v-model="filters.action">
            <option v-for="option in actionOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
        <div class="query-actions">
          <button type="button" class="btn-primary" @click="search">搜索</button>
          <button type="button" class="btn-default" @click="resetFilters">重置</button>
        </div>
      </div>
    </section>

    <section class="table-card">
      <div class="toolbar">
        <div class="toolbar-title">操作日志</div>
        <div class="toolbar-meta">共 {{ total }} 条</div>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
      <div v-if="loading" class="table-placeholder">加载中...</div>
      <div v-else-if="!items.length" class="table-placeholder">暂无日志</div>

      <div v-else class="table-wrap">
        <table class="audit-table">
          <thead>
            <tr>
              <th class="col-id">ID</th>
              <th>时间</th>
              <th>操作者</th>
              <th>资源类型</th>
              <th>资源 ID</th>
              <th>动作</th>
              <th class="col-action">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td>{{ item.id }}</td>
              <td>{{ formatDate(item.created_at) }}</td>
              <td>
                <div class="operator">
                  <strong>{{ operatorName(item) }}</strong>
                  <span v-if="item.username && item.nickname">{{ item.username }}</span>
                </div>
              </td>
              <td><span class="tag">{{ item.resource_type }}</span></td>
              <td>{{ item.resource_id || '-' }}</td>
              <td><span class="action-tag">{{ item.action }}</span></td>
              <td>
                <button type="button" class="text-btn" @click="openDetail(item)">查看</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="total > 0" class="pagination">
        <span class="page-info">第 {{ pageStart }}-{{ pageEnd }} 条 / 共 {{ total }} 条</span>
        <button type="button" :disabled="currentPage <= 1" @click="goToPage(currentPage - 1)">上一页</button>
        <button
          v-for="page in visiblePages"
          :key="page"
          type="button"
          :class="{ active: page === currentPage }"
          @click="goToPage(page)"
        >
          {{ page }}
        </button>
        <button type="button" :disabled="currentPage >= totalPages" @click="goToPage(currentPage + 1)">下一页</button>
      </div>
    </section>

    <div v-if="detailVisible && detailItem" class="modal-mask" @click="closeDetail">
      <section class="modal" @click.stop>
        <div class="modal-head">
          <div>
            <h3>日志详情 #{{ detailItem.id }}</h3>
            <p>{{ formatDate(detailItem.created_at) }} · {{ detailItem.resource_type }} · {{ detailItem.action }}</p>
          </div>
          <button type="button" class="btn-text" @click="closeDetail">关闭</button>
        </div>
        <div class="modal-body">
          <section class="diff-panel">
            <div class="diff-head">
              <h4>差异对比</h4>
              <span>共 {{ detailDiffRows.length }} 处差异</span>
            </div>
            <div v-if="!detailDiffRows.length" class="diff-empty">变更前后没有字段差异</div>
            <div v-else class="diff-wrap">
              <table class="diff-table">
                <thead>
                  <tr>
                    <th>字段</th>
                    <th>变更前</th>
                    <th>变更后</th>
                    <th>类型</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in detailDiffRows" :key="row.path" :class="row.status">
                    <td class="diff-path">{{ row.path }}</td>
                    <td class="diff-value before">{{ formatDiffValue(row.before) }}</td>
                    <td class="diff-value after">{{ formatDiffValue(row.after) }}</td>
                    <td><span class="diff-status" :class="row.status">{{ diffStatusLabel(row.status) }}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

        <div class="detail-grid">
          <section class="json-panel">
            <h4>变更前</h4>
            <pre>{{ formatJson(detailItem.before_json) }}</pre>
          </section>
          <section class="json-panel">
            <h4>变更后</h4>
            <pre>{{ formatJson(detailItem.after_json) }}</pre>
          </section>
        </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.ops-page { display: grid; gap: 16px; }
.query-card,
.table-card { background: #fff; border: 1px solid #ebeef5; border-radius: 4px; padding: 16px 20px; }
.query-row { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; }
.query-item { display: grid; gap: 6px; min-width: 180px; }
.query-label { color: #606266; font-size: 13px; }
.query-item input,
.query-item select { height: 36px; border: 1px solid #dcdfe6; border-radius: 4px; padding: 0 12px; background: #fff; }
.query-actions { display: flex; gap: 8px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.toolbar-title { font-weight: 600; color: #303133; }
.toolbar-meta { color: #909399; font-size: 13px; }
.table-wrap { border: 1px solid #ebeef5; border-radius: 2px; overflow: auto; }
.audit-table { width: 100%; min-width: 920px; border-collapse: collapse; font-size: 13px; }
.audit-table th,
.audit-table td { border-bottom: 1px solid #ebeef5; border-right: 1px solid #ebeef5; padding: 10px 12px; text-align: center; vertical-align: middle; }
.audit-table th:last-child,
.audit-table td:last-child { border-right: none; }
.audit-table thead { background: #fafafa; }
.col-id { width: 80px; }
.col-action { width: 88px; }
.operator { display: grid; gap: 2px; }
.operator span { color: #909399; font-size: 12px; }
.tag,
.action-tag { display: inline-flex; align-items: center; height: 24px; border-radius: 12px; padding: 0 10px; background: #f4f4f5; color: #606266; }
.action-tag { background: #ecf5ff; color: #409eff; }
.text-btn { border: none; background: transparent; color: #409eff; cursor: pointer; font-size: 13px; padding: 0; }
.text-btn:hover { color: #66b1ff; }
.btn-primary,
.btn-default { height: 36px; border-radius: 4px; padding: 0 14px; cursor: pointer; }
.btn-primary { background: #409eff; border: 1px solid #409eff; color: #fff; }
.btn-default { background: #fff; border: 1px solid #dcdfe6; color: #606266; }
.table-placeholder { min-height: 180px; display: grid; place-items: center; color: #909399; border: 1px dashed #dcdfe6; border-radius: 2px; }
.error { color: #dc2626; background: #fef0f0; border: 1px solid #fde2e2; border-radius: 4px; padding: 10px 12px; margin-bottom: 10px; }
.pagination { display: flex; justify-content: flex-end; align-items: center; gap: 6px; margin-top: 14px; }
.pagination button { min-width: 34px; height: 32px; border: 1px solid #dcdfe6; background: #fff; color: #606266; border-radius: 4px; cursor: pointer; }
.pagination button.active { background: #409eff; border-color: #409eff; color: #fff; }
.pagination button:disabled { color: #c0c4cc; cursor: not-allowed; }
.page-info { margin-right: 8px; color: #909399; font-size: 13px; }
.modal-mask { position: fixed; inset: 0; display: grid; place-items: center; background: rgba(15, 23, 42, 0.34); padding: 24px; z-index: 1000; }
.modal { width: min(100%, 1080px); max-height: min(860px, calc(100vh - 48px)); overflow: hidden; background: #fff; border: 1px solid #ebeef5; border-radius: 4px; }
.modal-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; padding: 16px 20px; border-bottom: 1px solid #ebeef5; }
.modal-head h3 { margin: 0 0 6px; color: #303133; }
.modal-head p { margin: 0; color: #909399; font-size: 13px; }
.btn-text { border: none; background: transparent; color: #909399; cursor: pointer; }
.modal-body { max-height: calc(100vh - 126px); overflow: auto; padding: 16px 20px 20px; }
.diff-panel { border: 1px solid #ebeef5; border-radius: 4px; overflow: hidden; margin-bottom: 16px; }
.diff-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 10px 12px; background: #fafafa; }
.diff-head h4 { margin: 0; color: #606266; font-size: 13px; }
.diff-head span { color: #909399; font-size: 12px; }
.diff-empty { padding: 28px 12px; color: #909399; text-align: center; }
.diff-wrap { max-height: 320px; overflow: auto; }
.diff-table { width: 100%; min-width: 820px; border-collapse: collapse; font-size: 12px; }
.diff-table th,
.diff-table td { border-top: 1px solid #ebeef5; border-right: 1px solid #ebeef5; padding: 8px 10px; text-align: left; vertical-align: top; }
.diff-table th:last-child,
.diff-table td:last-child { border-right: none; text-align: center; width: 86px; }
.diff-table thead { background: #fff; color: #606266; }
.diff-table tr.added { background: #f0f9eb; }
.diff-table tr.deleted { background: #fef0f0; }
.diff-table tr.changed { background: #fdf6ec; }
.diff-path { width: 220px; color: #303133; font-family: Consolas, 'Courier New', monospace; word-break: break-all; }
.diff-value { max-width: 280px; white-space: pre-wrap; word-break: break-all; font-family: Consolas, 'Courier New', monospace; }
.diff-value.before { color: #7c2d12; }
.diff-value.after { color: #14532d; }
.diff-status { display: inline-flex; align-items: center; height: 22px; border-radius: 11px; padding: 0 8px; font-size: 12px; }
.diff-status.added { background: #e1f3d8; color: #67c23a; }
.diff-status.deleted { background: #fde2e2; color: #f56c6c; }
.diff-status.changed { background: #faecd8; color: #e6a23c; }
.detail-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.json-panel { min-width: 0; border: 1px solid #ebeef5; border-radius: 4px; overflow: hidden; }
.json-panel h4 { margin: 0; padding: 10px 12px; background: #fafafa; color: #606266; font-size: 13px; }
.json-panel pre { min-height: 280px; max-height: 560px; margin: 0; padding: 12px; overflow: auto; background: #0f172a; color: #e5e7eb; font-size: 12px; line-height: 1.6; }

@media (max-width: 960px) {
  .query-item { width: 100%; }
  .detail-grid { grid-template-columns: 1fr; }
  .pagination { justify-content: flex-start; flex-wrap: wrap; }
}
</style>
