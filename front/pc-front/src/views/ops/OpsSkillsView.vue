<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import {
  clearOpsToken,
  createOpsSkill,
  deleteOpsSkill,
  fetchOpsMe,
  fetchOpsSkillDetail,
  fetchOpsSkillOptions,
  fetchOpsSkillUsages,
  fetchOpsSkills,
  showOpsToast,
  updateOpsSkill,
  uploadOpsSkillIcon,
  type OpsSkillItem,
  type OpsSkillUsageItem,
} from '@/api/ops'

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const keyword = ref('')
const attr = ref('')
const type = ref('')
const items = ref<OpsSkillItem[]>([])
const editingId = ref<number | null>(null)
const drawerVisible = ref(false)
const currentPage = ref(1)
const pageSize = 10
const total = ref(0)
const isAdmin = ref(false)

const attrOptions = ref<string[]>([])
const typeOptions = ref<string[]>([])

const form = reactive({
  name: '',
  attr: '',
  type: '',
  power: 0,
  consume: 0,
  skill_desc: '',
  icon: '',
  icon_url: '',
})

const pendingIconFile = ref<File | null>(null)
const pendingIconPreviewUrl = ref<string>('')
const iconFileInputRef = ref<HTMLInputElement | null>(null)

const usagesVisible = ref(false)
const usagesLoading = ref(false)
const usagesTarget = ref<OpsSkillItem | null>(null)
const usages = ref<OpsSkillUsageItem[]>([])

const iconDisplaySrc = computed(() => pendingIconPreviewUrl.value || form.icon_url || '')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const pageStart = computed(() => (total.value === 0 ? 0 : (currentPage.value - 1) * pageSize + 1))
const pageEnd = computed(() => Math.min(currentPage.value * pageSize, total.value))
const visiblePages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  for (let page = start; page <= end; page += 1) pages.push(page)
  return pages
})

function revokePendingIcon() {
  if (pendingIconPreviewUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(pendingIconPreviewUrl.value)
  }
  pendingIconPreviewUrl.value = ''
  pendingIconFile.value = null
}

function resetForm() {
  editingId.value = null
  form.name = ''
  form.attr = ''
  form.type = ''
  form.power = 0
  form.consume = 0
  form.skill_desc = ''
  form.icon = ''
  form.icon_url = ''
  revokePendingIcon()
  if (iconFileInputRef.value) iconFileInputRef.value.value = ''
}

function openCreateDrawer() {
  resetForm()
  drawerVisible.value = true
}

function closeDrawer() {
  drawerVisible.value = false
}

function onIconFileSelected(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  revokePendingIcon()
  pendingIconFile.value = file
  pendingIconPreviewUrl.value = URL.createObjectURL(file)
}

function clearIcon() {
  revokePendingIcon()
  form.icon = ''
  form.icon_url = ''
  if (iconFileInputRef.value) iconFileInputRef.value.value = ''
}

async function editItem(item: OpsSkillItem) {
  try {
    const detail = await fetchOpsSkillDetail(item.id)
    editingId.value = detail.id
    form.name = detail.name
    form.attr = detail.attr
    form.type = detail.type
    form.power = detail.power
    form.consume = detail.consume
    form.skill_desc = detail.skill_desc
    form.icon = detail.icon
    form.icon_url = detail.icon_url
    revokePendingIcon()
    drawerVisible.value = true
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '加载失败', 'error')
  }
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [me, resp, options] = await Promise.all([
      fetchOpsMe(),
      fetchOpsSkills({
        keyword: keyword.value.trim() || undefined,
        attr: attr.value.trim() || undefined,
        type: type.value.trim() || undefined,
        page: currentPage.value,
        page_size: pageSize,
      }),
      fetchOpsSkillOptions(),
    ])
    isAdmin.value = me.role === 'admin'
    items.value = resp.items
    total.value = resp.total
    currentPage.value = resp.page
    attrOptions.value = options.attrs
    typeOptions.value = options.types
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

async function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  await loadData()
}

async function search() {
  currentPage.value = 1
  await loadData()
}

async function resetFilters() {
  keyword.value = ''
  attr.value = ''
  type.value = ''
  currentPage.value = 1
  await loadData()
}

async function submitForm() {
  if (saving.value) return
  saving.value = true
  error.value = ''
  try {
    if (pendingIconFile.value) {
      try {
        const data = await uploadOpsSkillIcon(pendingIconFile.value)
        form.icon = data.icon
        form.icon_url = data.preview_url
        revokePendingIcon()
      } catch (err: any) {
        showOpsToast(err?.response?.data?.detail || '图标上传失败', 'error')
        return
      }
    }
    const payload = {
      name: form.name.trim(),
      attr: form.attr.trim(),
      type: form.type.trim(),
      power: Number(form.power) || 0,
      consume: Number(form.consume) || 0,
      skill_desc: form.skill_desc.trim(),
      icon: form.icon.trim(),
    }
    if (editingId.value) {
      await updateOpsSkill(editingId.value, payload)
      showOpsToast('技能已更新', 'success')
    } else {
      await createOpsSkill(payload)
      showOpsToast('技能已创建', 'success')
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

async function removeItem(item: OpsSkillItem, force = false) {
  const suffix = force ? '，并解除所有精灵的引用' : ''
  if (!window.confirm(`确定删除技能 ${item.name} 吗？${suffix}`)) return
  try {
    await deleteOpsSkill(item.id, force)
    if (editingId.value === item.id) resetForm()
    await loadData()
    showOpsToast('技能已删除', 'success')
  } catch (err: any) {
    const detail = err?.response?.data?.detail || '删除失败'
    const status = err?.response?.status
    if (status === 409 && isAdmin.value) {
      if (window.confirm(`${detail}\n是否强制删除并解除所有引用？`)) {
        await removeItem(item, true)
      }
      return
    }
    showOpsToast(detail, 'error')
  }
}

async function openUsages(item: OpsSkillItem) {
  usagesTarget.value = item
  usagesVisible.value = true
  usagesLoading.value = true
  usages.value = []
  try {
    const resp = await fetchOpsSkillUsages(item.id)
    usages.value = resp.items
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '加载失败', 'error')
  } finally {
    usagesLoading.value = false
  }
}

function closeUsages() {
  usagesVisible.value = false
  usagesTarget.value = null
  usages.value = []
}

onMounted(() => {
  void loadData()
})

onBeforeUnmount(() => {
  revokePendingIcon()
})
</script>

<template>
  <div class="ops-page">
    <section class="query-card">
      <div class="query-row">
        <label class="query-item">
          <span class="query-label">技能名称</span>
          <input v-model="keyword" type="text" placeholder="请输入技能名称" />
        </label>
        <label class="query-item">
          <span class="query-label">属性</span>
          <select v-model="attr">
            <option value="">全部</option>
            <option v-for="opt in attrOptions" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </label>
        <label class="query-item">
          <span class="query-label">类型</span>
          <select v-model="type">
            <option value="">全部</option>
            <option v-for="opt in typeOptions" :key="opt" :value="opt">{{ opt }}</option>
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
        <button type="button" class="btn-primary" @click="openCreateDrawer">新增</button>
        <div class="toolbar-meta">共 {{ total }} 条</div>
      </div>

      <p v-if="error" class="error">{{ error }}</p>

      <div v-if="loading" class="table-placeholder muted">加载中...</div>
      <div v-else-if="!items.length" class="table-placeholder">
        <strong>暂无数据</strong>
        <span>请调整筛选条件后重试，或新增技能。</span>
      </div>
      <div v-else class="table-wrap">
        <table class="dict-table">
          <thead>
            <tr>
              <th class="col-index">序号</th>
              <th class="col-icon">图标</th>
              <th>技能名称</th>
              <th>属性</th>
              <th>类型</th>
              <th class="col-num">威力</th>
              <th class="col-num">消耗</th>
              <th class="col-desc">描述</th>
              <th class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td>
                <img v-if="item.icon_url" :src="item.icon_url" class="icon-thumb" alt="" />
                <span v-else class="muted">-</span>
              </td>
              <td class="label-cell">{{ item.name }}</td>
              <td>{{ item.attr || '-' }}</td>
              <td>{{ item.type || '-' }}</td>
              <td>{{ item.power }}</td>
              <td>{{ item.consume }}</td>
              <td class="desc-cell" :title="item.skill_desc">{{ item.skill_desc || '-' }}</td>
              <td>
                <div class="action-group">
                  <button type="button" class="text-btn" @click="editItem(item)">修改</button>
                  <button type="button" class="text-btn" @click="openUsages(item)">占用</button>
                  <button type="button" class="text-btn danger" @click="removeItem(item)">删除</button>
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
          <button
            type="button"
            class="pager-btn"
            :disabled="currentPage === totalPages"
            @click="goToPage(totalPages)"
          >
            末页
          </button>
        </div>
      </div>
    </section>

    <div v-if="drawerVisible" class="modal-mask" @click="closeDrawer">
      <section class="dict-modal" @click.stop>
        <div class="modal-head">
          <div>
            <h2>{{ editingId ? '编辑技能' : '新增技能' }}</h2>
          </div>
          <button type="button" class="modal-close" @click="closeDrawer">关闭</button>
        </div>

        <form class="dict-form" @submit.prevent="submitForm">
          <div class="form-grid">
            <label class="form-row">
              <span>技能名称</span>
              <input v-model="form.name" required type="text" maxlength="50" placeholder="请输入技能名称" />
            </label>
            <label class="form-row">
              <span>属性</span>
              <select v-model="form.attr">
                <option value="">请选择</option>
                <option v-for="opt in attrOptions" :key="opt" :value="opt">{{ opt }}</option>
              </select>
            </label>
            <label class="form-row">
              <span>类型</span>
              <select v-model="form.type">
                <option value="">请选择</option>
                <option v-for="opt in typeOptions" :key="opt" :value="opt">{{ opt }}</option>
              </select>
            </label>
            <label class="form-row">
              <span>威力</span>
              <input v-model.number="form.power" type="number" min="0" max="9999" />
            </label>
            <label class="form-row">
              <span>消耗</span>
              <input v-model.number="form.consume" type="number" min="0" max="9999" />
            </label>
            <label class="form-row full">
              <span>描述</span>
              <textarea v-model="form.skill_desc" rows="3" placeholder="技能描述" />
            </label>
            <div class="form-row full icon-row">
              <span>图标</span>
              <div class="icon-slot">
                <div class="icon-preview">
                  <img v-if="iconDisplaySrc" :src="iconDisplaySrc" alt="" />
                  <span v-else class="muted">无图标</span>
                </div>
                <div class="icon-actions">
                  <input
                    ref="iconFileInputRef"
                    type="file"
                    accept="image/*"
                    style="display: none"
                    @change="onIconFileSelected"
                  />
                  <button type="button" class="btn-default" @click="iconFileInputRef?.click()">选择图标</button>
                  <button type="button" class="btn-default" @click="clearIcon">清除</button>
                  <span class="icon-hint muted">点击保存时上传</span>
                </div>
              </div>
            </div>
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

    <div v-if="usagesVisible" class="modal-mask" @click="closeUsages">
      <section class="dict-modal" @click.stop>
        <div class="modal-head">
          <div>
            <h2>技能占用 - {{ usagesTarget?.name }}</h2>
          </div>
          <button type="button" class="modal-close" @click="closeUsages">关闭</button>
        </div>
        <div class="usages-body">
          <div v-if="usagesLoading" class="muted">加载中...</div>
          <div v-else-if="!usages.length" class="muted">该技能暂未被任何精灵使用</div>
          <table v-else class="dict-table">
            <thead>
              <tr>
                <th>编号</th>
                <th>精灵名</th>
                <th>来源</th>
                <th>排序</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in usages" :key="u.id">
                <td>{{ u.no }}</td>
                <td>{{ u.name }}</td>
                <td>{{ u.type }}</td>
                <td>{{ u.sort_order }}</td>
              </tr>
            </tbody>
          </table>
        </div>
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
.query-label {
  color: #606266;
  font-size: 13px;
  white-space: nowrap;
}
.query-item input,
.query-item select {
  width: 220px;
}
.query-actions {
  display: flex;
  gap: 10px;
  margin-left: 12px;
}
input,
select,
textarea {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #fff;
  color: #303133;
  padding: 0 14px;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
  font-family: inherit;
  font-size: 13px;
}
input,
select {
  height: 36px;
}
textarea {
  padding: 8px 14px;
  min-height: 72px;
  resize: vertical;
}
input:focus,
select:focus,
textarea:focus {
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
  width: 80px;
}
.col-icon {
  width: 72px;
}
.col-num {
  width: 80px;
}
.col-desc {
  max-width: 260px;
}
.desc-cell {
  max-width: 260px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.col-actions {
  width: 200px;
}
.label-cell {
  min-width: 140px;
}
.icon-thumb {
  width: 36px;
  height: 36px;
  object-fit: contain;
  vertical-align: middle;
}
.action-group {
  display: inline-flex;
  gap: 14px;
  justify-content: center;
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
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px 20px;
}
.form-row {
  display: grid;
  grid-template-columns: 80px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
}
.form-row.full {
  grid-column: 1 / -1;
  align-items: flex-start;
}
.form-row span {
  color: #606266;
  font-size: 13px;
}
.form-row input,
.form-row select,
.form-row textarea {
  width: 100%;
}
.icon-row {
  align-items: flex-start;
}
.icon-slot {
  display: flex;
  gap: 14px;
  align-items: center;
}
.icon-preview {
  width: 72px;
  height: 72px;
  border: 1px dashed #dcdfe6;
  border-radius: 4px;
  display: grid;
  place-items: center;
  background: #fafafa;
  overflow: hidden;
}
.icon-preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.icon-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.icon-hint {
  font-size: 12px;
}
.muted {
  color: var(--color-muted);
}
.modal-footer {
  margin-top: 20px;
  padding-top: 4px;
}
.error {
  color: #dc2626;
  background: #fef0f0;
  border: 1px solid #fde2e2;
  border-radius: 4px;
  padding: 10px 12px;
  margin-bottom: 12px;
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
  width: min(100%, 720px);
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
.dict-modal form,
.usages-body {
  padding: 8px 20px 20px;
  overflow: auto;
}
@media (max-width: 960px) {
  .query-item {
    width: 100%;
    flex-direction: column;
    align-items: flex-start;
  }
  .query-item input,
  .query-item select {
    width: 100%;
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
