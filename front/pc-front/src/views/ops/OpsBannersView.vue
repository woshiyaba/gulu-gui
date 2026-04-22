<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  clearOpsToken,
  createOpsBanner,
  deleteOpsBanner,
  fetchOpsBanners,
  fetchOpsDicts,
  fetchOpsMe,
  fetchOpsPokemonLineups,
  showOpsToast,
  updateOpsBanner,
  type OpsBannerItem,
  type OpsDictItem,
  type OpsPokemonLineupListItem,
} from '@/api/ops'

const LINEUP_TYPE_DICT = 'pokemon_lineup_type'

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const items = ref<OpsBannerItem[]>([])
const editingId = ref<number | null>(null)
const drawerVisible = ref(false)
const currentPage = ref(1)
const pageSize = 10
const total = ref(0)

const form = reactive({
  title: '',
  image_url: '',
  link_type: '',
  link_param: '',
  sort_order: 0,
  is_active: true,
})

const isAdmin = ref(false)
const lineupTypeOptions = ref<OpsDictItem[]>([])
const lineupOptions = ref<OpsPokemonLineupListItem[]>([])
const lineupLoading = ref(false)
const selectedLineupIds = ref<number[]>([])

const currentDictItem = computed(() =>
  lineupTypeOptions.value.find((d) => d.code === form.link_type),
)
const isMultiMode = computed(() => currentDictItem.value?.extra === 'multi')
const hasLinkType = computed(() => !!form.link_type)

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

function linkTypeLabel(code: string): string {
  if (!code) return '不跳转'
  return lineupTypeOptions.value.find((d) => d.code === code)?.label || code
}

function linkParamLabel(item: OpsBannerItem): string {
  if (!item.link_param) return '-'
  const ids = item.link_param.split(',').map(Number).filter(Boolean)
  const titles = ids
    .map((id) => lineupOptionsCache.value.get(id) || `#${id}`)
    .join('、')
  return titles || item.link_param
}

// 缓存所有已加载过的阵容 id→title 映射，用于列表展示
const lineupOptionsCache = ref<Map<number, string>>(new Map())

function updateCache(lineups: OpsPokemonLineupListItem[]) {
  for (const l of lineups) {
    lineupOptionsCache.value.set(l.id, l.title || `阵容#${l.id}`)
  }
}

async function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  await loadData()
}

function resetForm() {
  editingId.value = null
  form.title = ''
  form.image_url = ''
  form.link_type = ''
  form.link_param = ''
  form.sort_order = 0
  form.is_active = true
  selectedLineupIds.value = []
  lineupOptions.value = []
}

function openCreateDrawer() {
  resetForm()
  drawerVisible.value = true
}

function closeDrawer() {
  drawerVisible.value = false
}

function editItem(item: OpsBannerItem) {
  editingId.value = item.id
  form.title = item.title
  form.image_url = item.image_url
  form.link_type = item.link_type
  form.link_param = item.link_param
  form.sort_order = item.sort_order
  form.is_active = item.is_active

  if (item.link_param) {
    selectedLineupIds.value = item.link_param.split(',').map(Number).filter(Boolean)
  } else {
    selectedLineupIds.value = []
  }
  drawerVisible.value = true

  if (item.link_type) {
    void loadLineupsForType(item.link_type)
  }
}

async function loadLineupsForType(sourceType: string) {
  if (!sourceType) {
    lineupOptions.value = []
    return
  }
  lineupLoading.value = true
  try {
    const resp = await fetchOpsPokemonLineups({
      source_type: sourceType,
      page: 1,
      page_size: 200,
    })
    lineupOptions.value = resp.items
    updateCache(resp.items)
  } catch {
    lineupOptions.value = []
  } finally {
    lineupLoading.value = false
  }
}

// 用于首次加载时，把所有 banner 引用的阵容 ID 都批量拉标题
async function preloadLineupTitles(bannerItems: OpsBannerItem[]) {
  const allIds = new Set<number>()
  for (const b of bannerItems) {
    if (b.link_param) {
      b.link_param.split(',').map(Number).filter(Boolean).forEach((id) => allIds.add(id))
    }
  }
  const missingIds = [...allIds].filter((id) => !lineupOptionsCache.value.has(id))
  if (missingIds.length === 0) return

  // 按类型分组拉取
  const typeSet = new Set(bannerItems.map((b) => b.link_type).filter(Boolean))
  for (const t of typeSet) {
    try {
      const resp = await fetchOpsPokemonLineups({ source_type: t, page: 1, page_size: 200 })
      updateCache(resp.items)
    } catch { /* ignore */ }
  }
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [me, data] = await Promise.all([
      fetchOpsMe(),
      fetchOpsBanners({ page: currentPage.value, page_size: pageSize }),
    ])
    isAdmin.value = me.role === 'admin'
    items.value = data.items
    total.value = data.total
    currentPage.value = data.page
    await preloadLineupTitles(data.items)
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

async function submitForm() {
  if (saving.value) return
  saving.value = true
  error.value = ''
  try {
    const linkParam = isMultiMode.value
      ? selectedLineupIds.value.join(',')
      : (selectedLineupIds.value[0]?.toString() || '')

    const payload = {
      title: form.title.trim(),
      image_url: form.image_url.trim(),
      link_type: form.link_type.trim(),
      link_param: form.link_type ? linkParam : '',
      sort_order: Number(form.sort_order) || 0,
      is_active: form.is_active,
    }
    if (editingId.value) {
      await updateOpsBanner(editingId.value, payload)
      showOpsToast('Banner已更新', 'success')
    } else {
      await createOpsBanner(payload)
      showOpsToast('Banner已创建', 'success')
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

async function removeItem(item: OpsBannerItem) {
  if (!isAdmin.value) return
  if (!window.confirm(`确定删除 Banner「${item.title}」吗？`)) return
  try {
    await deleteOpsBanner(item.id)
    if (editingId.value === item.id) resetForm()
    await loadData()
    showOpsToast('Banner已删除', 'success')
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '删除失败'
    showOpsToast(error.value, 'error')
  }
}

function toggleLineupSelection(id: number) {
  if (isMultiMode.value) {
    const idx = selectedLineupIds.value.indexOf(id)
    if (idx >= 0) {
      selectedLineupIds.value.splice(idx, 1)
    } else {
      selectedLineupIds.value.push(id)
    }
  } else {
    selectedLineupIds.value = [id]
  }
}

function isLineupSelected(id: number): boolean {
  return selectedLineupIds.value.includes(id)
}

watch(() => form.link_type, (newType, oldType) => {
  if (newType !== oldType) {
    selectedLineupIds.value = []
    form.link_param = ''
    void loadLineupsForType(newType)
  }
})

onMounted(async () => {
  try {
    const resp = await fetchOpsDicts({ dict_type: LINEUP_TYPE_DICT, page: 1, page_size: 100 })
    lineupTypeOptions.value = resp.items
  } catch { /* ignore */ }
  void loadData()
})
</script>

<template>
  <div class="ops-page">
    <section class="table-card">
      <div class="toolbar">
        <button type="button" class="btn-primary" @click="openCreateDrawer">新增</button>
        <div class="toolbar-meta">共 {{ total }} 条</div>
      </div>

      <p v-if="error" class="error">{{ error }}</p>

      <div v-if="loading" class="table-placeholder muted">加载中...</div>
      <div v-else-if="!items.length" class="table-placeholder">
        <strong>暂无数据</strong>
        <span>点击「新增」添加 Banner。</span>
      </div>
      <div v-else class="table-wrap">
        <table class="tbl">
          <thead>
            <tr>
              <th class="col-index">序号</th>
              <th>标题</th>
              <th>图片预览</th>
              <th>跳转类型</th>
              <th>跳转阵容</th>
              <th class="col-sort">排序</th>
              <th>状态</th>
              <th class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td>{{ item.title }}</td>
              <td>
                <img v-if="item.image_url" :src="item.image_url" class="preview-img" />
                <span v-else class="muted">无</span>
              </td>
              <td>{{ linkTypeLabel(item.link_type) }}</td>
              <td>{{ linkParamLabel(item) }}</td>
              <td>{{ item.sort_order }}</td>
              <td>
                <span :class="item.is_active ? 'tag-active' : 'tag-inactive'">
                  {{ item.is_active ? '启用' : '禁用' }}
                </span>
              </td>
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
          <button type="button" class="pager-btn" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">上一页</button>
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
          <button type="button" class="pager-btn" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">下一页</button>
          <button type="button" class="pager-btn" :disabled="currentPage === totalPages" @click="goToPage(totalPages)">末页</button>
        </div>
      </div>
    </section>

    <div v-if="drawerVisible" class="modal-mask" @click="closeDrawer">
      <section class="modal" @click.stop>
        <div class="modal-head">
          <h2>{{ editingId ? '编辑Banner' : '新增Banner' }}</h2>
          <button type="button" class="modal-close" @click="closeDrawer">关闭</button>
        </div>

        <form class="modal-body" @submit.prevent="submitForm">
          <div class="form-grid">
            <label class="form-row">
              <span>标题</span>
              <input v-model="form.title" type="text" placeholder="Banner标题" />
            </label>
            <label class="form-row">
              <span>图片URL</span>
              <input v-model="form.image_url" required type="text" placeholder="Banner图片地址" />
            </label>
            <label class="form-row">
              <span>跳转类型</span>
              <select v-model="form.link_type">
                <option value="">不跳转</option>
                <option v-for="opt in lineupTypeOptions" :key="opt.code" :value="opt.code">
                  {{ opt.label }}
                </option>
              </select>
            </label>
            <label class="form-row">
              <span>排序</span>
              <input v-model="form.sort_order" type="number" placeholder="排序值" />
            </label>
            <label class="form-row">
              <span>状态</span>
              <select v-model="form.is_active">
                <option :value="true">启用</option>
                <option :value="false">禁用</option>
              </select>
            </label>
          </div>

          <!-- 阵容选择区域 -->
          <div v-if="hasLinkType" class="lineup-selector">
            <div class="lineup-selector-head">
              <span class="lineup-selector-label">
                选择阵容{{ isMultiMode ? '（可多选）' : '' }}
              </span>
              <span v-if="selectedLineupIds.length > 0" class="lineup-selector-count">
                已选 {{ selectedLineupIds.length }} 条
              </span>
            </div>

            <div v-if="lineupLoading" class="lineup-loading">加载阵容中...</div>
            <div v-else-if="lineupOptions.length === 0" class="lineup-empty">
              该类型暂无阵容数据
            </div>
            <div v-else class="lineup-list">
              <div
                v-for="lineup in lineupOptions"
                :key="lineup.id"
                class="lineup-item"
                :class="{ selected: isLineupSelected(lineup.id) }"
                @click="toggleLineupSelection(lineup.id)"
              >
                <span class="lineup-check">{{ isLineupSelected(lineup.id) ? '✓' : '' }}</span>
                <span class="lineup-title">{{ lineup.title || `阵容#${lineup.id}` }}</span>
                <span class="lineup-meta">
                  {{ lineup.member_count }}只 · 排序{{ lineup.sort_order }}
                  <template v-if="!lineup.is_active"> · 已禁用</template>
                </span>
              </div>
            </div>
          </div>

          <div v-if="form.image_url" class="preview-section">
            <span class="preview-label">图片预览</span>
            <img :src="form.image_url" class="preview-large" />
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

.table-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 2px;
  padding: 16px 20px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.toolbar-meta {
  font-size: 13px;
  color: #909399;
}

.form-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.btn-primary,
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

.btn-secondary {
  border: 1px solid #dcdfe6;
  background: #fff;
  color: #606266;
}

.btn-secondary:hover {
  color: #409eff;
  border-color: #c6e2ff;
  background: #ecf5ff;
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

.tbl th,
.tbl td {
  padding: 11px 14px;
  border-bottom: 1px solid #ebeef5;
  border-right: 1px solid #ebeef5;
  text-align: center;
  vertical-align: middle;
}

.tbl th:last-child,
.tbl td:last-child {
  border-right: none;
}

.tbl thead {
  background: #fafafa;
}

.tbl th {
  color: #909399;
  font-weight: 600;
}

.tbl tbody tr:hover {
  background: #f5f7fa;
}

.col-index {
  width: 60px;
}

.col-sort {
  width: 70px;
}

.col-actions {
  width: 140px;
}

.preview-img {
  max-width: 120px;
  max-height: 48px;
  border-radius: 4px;
  object-fit: cover;
}

.tag-active {
  color: #67c23a;
  font-size: 13px;
}

.tag-inactive {
  color: #909399;
  font-size: 13px;
}

.action-group {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
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

.pagination {
  margin-top: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  flex-wrap: wrap;
}

.pagination-summary {
  color: #606266;
  font-size: 13px;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 4px;
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
  border-color: #ebeef5;
}

.table-placeholder {
  min-height: 220px;
  border: 1px dashed #dcdfe6;
  border-radius: 2px;
  display: grid;
  place-items: center;
  text-align: center;
  color: #909399;
  padding: 24px;
}

.muted {
  color: #909399;
}

.error {
  color: #dc2626;
  background: #fef0f0;
  border: 1px solid #fde2e2;
  border-radius: 4px;
  padding: 10px 12px;
  margin-bottom: 12px;
}

input,
select {
  height: 36px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #fff;
  color: #303133;
  padding: 0 14px;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

input:focus,
select:focus {
  outline: none;
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.12);
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

.modal {
  width: min(100%, 640px);
  max-height: calc(100vh - 48px);
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
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

.modal-body {
  padding: 8px 20px 20px;
  overflow: auto;
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

.form-row input,
.form-row select {
  width: 100%;
}

/* 阵容选择器 */
.lineup-selector {
  margin-top: 18px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 14px;
}

.lineup-selector-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.lineup-selector-label {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.lineup-selector-count {
  font-size: 12px;
  color: #409eff;
}

.lineup-loading,
.lineup-empty {
  text-align: center;
  padding: 16px 0;
  color: #909399;
  font-size: 13px;
}

.lineup-list {
  max-height: 240px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.lineup-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.lineup-item:hover {
  background: #f5f7fa;
}

.lineup-item.selected {
  background: #ecf5ff;
  border: 1px solid #b3d8ff;
}

.lineup-check {
  width: 18px;
  height: 18px;
  border: 1px solid #dcdfe6;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #409eff;
  flex-shrink: 0;
}

.lineup-item.selected .lineup-check {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
}

.lineup-title {
  font-size: 13px;
  color: #303133;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lineup-meta {
  font-size: 12px;
  color: #909399;
  flex-shrink: 0;
}

.preview-section {
  margin-top: 18px;
}

.preview-label {
  display: block;
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}

.preview-large {
  max-width: 100%;
  max-height: 200px;
  border-radius: 4px;
  border: 1px solid #ebeef5;
}

.modal-footer {
  margin-top: 20px;
  padding-top: 4px;
}

@media (max-width: 960px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .form-row {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .modal {
    width: 100%;
  }
}
</style>
