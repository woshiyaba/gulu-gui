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

function extractChangeSummary(item: OpsAuditLogItem): string {
  const src = item.after_json || item.before_json
  if (src) {
    if (typeof src.name === 'string' && src.name) return src.name
    if (typeof src.nickname === 'string' && src.nickname) return src.nickname
    if (typeof src.username === 'string' && src.username) return src.username
    if (typeof src.title === 'string' && src.title) return src.title
    if (typeof src.display_name === 'string' && src.display_name) return src.display_name
    if (typeof src.key === 'string' && src.key) return src.key
  }
  const labels: Record<string, string> = {
    pokemon: '精灵',
    skill: '技能',
    skill_stone: '技能石',
    resonance_magic: '共鸣魔法',
    ops_user: '运营账号',
    sys_dict: '字典项',
    banner: 'Banner',
    evolution_chain: '进化链',
  }
  return labels[item.resource_type] || item.resource_type
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
    <section class="ops-card-padded">
      <div class="ops-filter-bar" style="align-items:flex-end;flex-wrap:wrap;margin-bottom:16px;">
        <label class="ops-form-item" style="min-width:180px;">
          <span class="ops-filter-label">操作者</span>
          <input v-model="filters.username" class="ops-input" type="text" placeholder="账号或昵称" @keyup.enter="search" />
        </label>
        <label class="ops-form-item" style="min-width:180px;">
          <span class="ops-filter-label">资源类型</span>
          <input v-model="filters.resource_type" class="ops-input" type="text" placeholder="如 pokemon / skill" @keyup.enter="search" />
        </label>
<label class="ops-form-item" style="min-width:150px;">
          <span class="ops-filter-label">动作</span>
          <select v-model="filters.action" class="ops-select">
            <option v-for="option in actionOptions" :key="option.value" :value="option.value">
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
        <span class="ops-section-title">操作日志</span>
        <span class="ops-toolbar-meta">共 {{ total }} 条</span>
      </div>

      <p v-if="error" class="ops-error">{{ error }}</p>
      <div v-if="loading" class="ops-loading">加载中...</div>
      <div v-else-if="!items.length" class="ops-empty">暂无日志</div>

      <div v-else class="ops-table-wrap">
        <table class="ops-table" style="min-width:920px;">
          <thead>
            <tr>
              <th style="width:80px;">序号</th>
              <th>时间</th>
              <th>操作者</th>
              <th>资源类型</th>
              <th>变更摘要</th>
              <th>动作</th>
              <th style="width:88px;">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td>{{ items.indexOf(item) + 1 }}</td>
              <td>{{ formatDate(item.created_at) }}</td>
              <td>
                <div style="display:grid;gap:2px;">
                  <strong>{{ operatorName(item) }}</strong>
                  <span v-if="item.username && item.nickname" style="color:var(--ops-muted);font-size:12px;">{{ item.username }}</span>
                </div>
              </td>
              <td><span class="ops-badge ops-badge--default">{{ item.resource_type }}</span></td>
              <td style="font-weight:500;">{{ extractChangeSummary(item) }}</td>
              <td><span class="ops-badge ops-badge--accent">{{ item.action }}</span></td>
              <td>
                <button type="button" class="ops-btn ops-btn-text" @click="openDetail(item)">查看</button>
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

    <div v-if="detailVisible && detailItem" class="ops-modal-mask" @click="closeDetail">
      <section class="ops-modal ops-modal-wide" @click.stop>
        <div class="ops-modal-header">
          <div>
            <h3>日志详情 #{{ detailItem.id }}</h3>
            <p style="margin:4px 0 0;color:var(--ops-muted);font-size:13px;">{{ formatDate(detailItem.created_at) }} · {{ detailItem.resource_type }} · {{ detailItem.action }}</p>
          </div>
          <button type="button" class="ops-btn ops-btn-text" @click="closeDetail">关闭</button>
        </div>
        <div class="ops-modal-body">
          <section style="border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);overflow:hidden;margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 12px;background:var(--ops-bg);">
              <h4 style="margin:0;color:var(--ops-text-secondary);font-size:13px;font-weight:600;">差异对比</h4>
              <span style="color:var(--ops-muted);font-size:12px;">共 {{ detailDiffRows.length }} 处差异</span>
            </div>
            <div v-if="!detailDiffRows.length" style="padding:28px 12px;color:var(--ops-muted);text-align:center;">变更前后没有字段差异</div>
            <div v-else style="max-height:320px;overflow:auto;">
              <table style="width:100%;min-width:820px;border-collapse:collapse;font-size:12px;">
                <thead>
                  <tr>
                    <th style="border-top:1px solid var(--ops-border);padding:8px 10px;text-align:left;color:var(--ops-text-secondary);background:#fff;">字段</th>
                    <th style="border-top:1px solid var(--ops-border);padding:8px 10px;text-align:left;color:var(--ops-text-secondary);background:#fff;">变更前</th>
                    <th style="border-top:1px solid var(--ops-border);padding:8px 10px;text-align:left;color:var(--ops-text-secondary);background:#fff;">变更后</th>
                    <th style="border-top:1px solid var(--ops-border);padding:8px 10px;text-align:center;color:var(--ops-text-secondary);background:#fff;width:86px;">类型</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in detailDiffRows" :key="row.path" :style="{
                    background: row.status === 'added' ? 'var(--ops-success-light)' : row.status === 'deleted' ? 'var(--ops-danger-light)' : 'var(--ops-warning-light)'
                  }">
                    <td style="width:220px;padding:8px 10px;border-top:1px solid var(--ops-border);font-family:Consolas,monospace;word-break:break-all;color:var(--ops-text);">{{ row.path }}</td>
                    <td style="max-width:280px;padding:8px 10px;border-top:1px solid var(--ops-border);font-family:Consolas,monospace;white-space:pre-wrap;word-break:break-all;color:#7c2d12;">{{ formatDiffValue(row.before) }}</td>
                    <td style="max-width:280px;padding:8px 10px;border-top:1px solid var(--ops-border);font-family:Consolas,monospace;white-space:pre-wrap;word-break:break-all;color:#14532d;">{{ formatDiffValue(row.after) }}</td>
                    <td style="padding:8px 10px;border-top:1px solid var(--ops-border);text-align:center;">
                      <span class="ops-badge" :class="row.status === 'added' ? 'ops-badge--success' : row.status === 'deleted' ? 'ops-badge--danger' : 'ops-badge--warning'" style="height:22px;font-size:12px;">{{ diffStatusLabel(row.status) }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:16px;">
            <section style="border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);overflow:hidden;">
              <h4 style="margin:0;padding:10px 12px;background:var(--ops-bg);color:var(--ops-text-secondary);font-size:13px;">变更前</h4>
              <pre style="min-height:280px;max-height:560px;margin:0;padding:12px;overflow:auto;background:#0f172a;color:#e5e7eb;font-size:12px;line-height:1.6;">{{ formatJson(detailItem.before_json) }}</pre>
            </section>
            <section style="border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);overflow:hidden;">
              <h4 style="margin:0;padding:10px 12px;background:var(--ops-bg);color:var(--ops-text-secondary);font-size:13px;">变更后</h4>
              <pre style="min-height:280px;max-height:560px;margin:0;padding:12px;overflow:auto;background:#0f172a;color:#e5e7eb;font-size:12px;line-height:1.6;">{{ formatJson(detailItem.after_json) }}</pre>
            </section>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
