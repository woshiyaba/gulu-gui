<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import {
  clearOpsToken,
  createOpsResonanceMagic,
  deleteOpsResonanceMagic,
  fetchOpsMe,
  fetchOpsResonanceMagics,
  showOpsToast,
  updateOpsResonanceMagic,
  uploadOpsResonanceMagicIcon,
  type OpsResonanceMagicItem,
} from '@/api/ops'

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const keyword = ref('')
const items = ref<OpsResonanceMagicItem[]>([])
const editingId = ref<number | null>(null)
const modalVisible = ref(false)
const currentPage = ref(1)
const pageSize = 10
const total = ref(0)
const isAdmin = ref(false)
const pendingIconFile = ref<File | null>(null)
const pendingIconPreviewUrl = ref('')
const iconFileInputRef = ref<HTMLInputElement | null>(null)

const form = reactive({
  id: 0,
  name: '',
  description: '',
  max_usage_count: 1,
  icon: '',
  icon_url: '',
  sort_order: 0,
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const pageStart = computed(() => {
  if (total.value === 0) return 0
  return (currentPage.value - 1) * pageSize + 1
})
const pageEnd = computed(() => Math.min(currentPage.value * pageSize, total.value))
const visiblePages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  for (let p = start; p <= end; p += 1) {
    pages.push(p)
  }
  return pages
})

const iconDisplaySrc = computed(() => {
  if (pendingIconPreviewUrl.value) return pendingIconPreviewUrl.value
  return (form.icon_url || '').trim()
})

function revokePendingPreview() {
  if (pendingIconPreviewUrl.value) {
    URL.revokeObjectURL(pendingIconPreviewUrl.value)
    pendingIconPreviewUrl.value = ''
  }
}

function resetPendingIcon() {
  pendingIconFile.value = null
  revokePendingPreview()
}

function triggerIconFilePick() {
  iconFileInputRef.value?.click()
}

function clearIconImage() {
  resetPendingIcon()
  form.icon = ''
  form.icon_url = ''
}

function onIconImageSelected(ev: Event) {
  const el = ev.target as HTMLInputElement
  const file = el.files?.[0]
  if (!file) return
  revokePendingPreview()
  pendingIconFile.value = file
  pendingIconPreviewUrl.value = URL.createObjectURL(file)
  el.value = ''
}

async function goToPage(target: number) {
  if (target < 1 || target > totalPages.value || target === currentPage.value) return
  currentPage.value = target
  await loadData()
}

function resetForm() {
  editingId.value = null
  form.id = 0
  form.name = ''
  form.description = ''
  form.max_usage_count = 1
  form.icon = ''
  form.icon_url = ''
  form.sort_order = 0
  resetPendingIcon()
}

function openCreateModal() {
  resetForm()
  modalVisible.value = true
}

function editItem(item: OpsResonanceMagicItem) {
  editingId.value = item.id
  form.id = item.id
  form.name = item.name
  form.description = item.description
  form.max_usage_count = item.max_usage_count
  form.icon = item.icon
  form.icon_url = item.icon_url || ''
  form.sort_order = item.sort_order
  resetPendingIcon()
  modalVisible.value = true
}

function closeModal() {
  modalVisible.value = false
  resetPendingIcon()
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [me, data] = await Promise.all([
      fetchOpsMe(),
      fetchOpsResonanceMagics({
        keyword: keyword.value.trim() || undefined,
        page: currentPage.value,
        page_size: pageSize,
      }),
    ])
    isAdmin.value = me.role === 'admin'
    items.value = data.items
    total.value = data.total
    currentPage.value = data.page
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

async function submit() {
  if (saving.value) return
  saving.value = true
  error.value = ''
  try {
    let icon = form.icon.trim()
    if (pendingIconFile.value) {
      const result = await uploadOpsResonanceMagicIcon(pendingIconFile.value)
      icon = result.icon
      form.icon_url = result.preview_url
    }
    const payload = {
      name: form.name.trim(),
      description: form.description.trim(),
      max_usage_count: Number(form.max_usage_count) || 1,
      icon,
      sort_order: Number(form.sort_order) || 0,
    }
    if (editingId.value) {
      await updateOpsResonanceMagic(editingId.value, payload)
      showOpsToast('共鸣魔法已更新', 'success')
    } else {
      await createOpsResonanceMagic(payload)
      showOpsToast('共鸣魔法已创建', 'success')
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

async function removeItem(item: OpsResonanceMagicItem) {
  if (!isAdmin.value) return
  if (!window.confirm(`确定删除共鸣魔法「${item.name}」吗？`)) return
  try {
    await deleteOpsResonanceMagic(item.id)
    if (editingId.value === item.id) resetForm()
    await loadData()
    showOpsToast('共鸣魔法已删除', 'success')
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '删除失败', 'error')
  }
}

onMounted(() => {
  void loadData()
})

onBeforeUnmount(() => {
  revokePendingPreview()
})
</script>

<template>
  <div class="ops-page">
    <section class="query-card">
      <div class="query-row">
        <label class="query-item">
          <span class="query-label">关键字</span>
          <input v-model="keyword" class="keyword-input" type="text" placeholder="共鸣魔法名称" @keyup.enter="search" />
        </label>
        <div class="query-actions">
          <button type="button" class="btn-primary" @click="search">查询</button>
          <button type="button" class="btn-secondary" @click="resetFilters">重置</button>
        </div>
      </div>
    </section>

    <section class="table-card">
      <div class="toolbar">
        <button v-if="isAdmin" type="button" class="btn-primary" @click="openCreateModal">新增共鸣魔法</button>
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
              <th>名称</th>
              <th>描述</th>
              <th>可使用次数</th>
              <th>排序</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ (currentPage - 1) * pageSize + index + 1 }}</td>
              <td>{{ item.name }}</td>
              <td>{{ item.description || '—' }}</td>
              <td>{{ item.max_usage_count }}</td>
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
        <div class="pager-summary">共 {{ total }} 条，当前显示 {{ pageStart }}-{{ pageEnd }} 条</div>
        <div class="pager-controls">
          <button type="button" class="pager-btn" :disabled="currentPage === 1" @click="goToPage(1)">首页</button>
          <button type="button" class="pager-btn" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">上一页</button>
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
          <button type="button" class="pager-btn" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">下一页</button>
          <button type="button" class="pager-btn" :disabled="currentPage === totalPages" @click="goToPage(totalPages)">末页</button>
        </div>
      </div>
    </section>

    <div v-if="modalVisible" class="modal-mask">
      <section class="modal" @click.stop>
        <div class="modal-head">
          <h3>{{ editingId ? '编辑共鸣魔法' : '新增共鸣魔法' }}</h3>
        </div>
        <form class="modal-body" @submit.prevent="submit">
          <section class="section-card section-with-icon">
            <h4>基础信息</h4>
            <div class="basic-with-icon">
              <div class="basic-with-icon-fields">
                <label><span>名称</span><input v-model="form.name" required type="text" placeholder="例：元素共鸣" maxlength="50" /></label>
                <label><span>可使用次数</span><input v-model.number="form.max_usage_count" required type="number" min="1" placeholder="例：1" /></label>
                <label><span>排序</span><input v-model.number="form.sort_order" type="number" placeholder="越小越靠前" /></label>
              </div>
              <aside class="basic-with-icon-side" aria-label="图标">
                <div class="basic-icon-heading">图标</div>
                <div class="icon-upload-area">
                  <button
                    type="button"
                    class="icon-preview"
                    :disabled="saving"
                    @click="triggerIconFilePick"
                  >
                    <img v-if="iconDisplaySrc" :src="iconDisplaySrc" alt="" class="icon-preview-img" />
                    <div v-else class="icon-placeholder-inner">
                      <span class="icon-placeholder-title">暂无</span>
                      <span class="icon-placeholder-sub">点击上传</span>
                    </div>
                  </button>
                  <input
                    ref="iconFileInputRef"
                    type="file"
                    class="icon-file-hidden"
                    accept=".webp,.png,.jpg,.jpeg,.gif,image/webp,image/png,image/jpeg,image/gif"
                    :disabled="saving"
                    @change="onIconImageSelected"
                  />
                  <div class="icon-actions">
                    <button type="button" class="btn-primary btn-compact" :disabled="saving" @click="triggerIconFilePick">
                      {{ iconDisplaySrc ? '更换' : '选择图片' }}
                    </button>
                    <button
                      v-if="form.icon || pendingIconFile"
                      type="button"
                      class="btn-secondary btn-compact"
                      :disabled="saving"
                      @click="clearIconImage"
                    >
                      移除
                    </button>
                  </div>
                </div>
              </aside>
            </div>
          </section>

          <section class="section-card full">
            <h4>描述</h4>
            <textarea v-model="form.description" rows="4" placeholder="请输入共鸣魔法描述" />
          </section>

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

.query-card,
.table-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 16px;
}

.query-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.query-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.query-label {
  font-size: 13px;
  color: #606266;
  line-height: 1;
  white-space: nowrap;
  min-width: 56px;
}

.keyword-input {
  width: 180px;
  height: 36px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 0 12px;
  color: #606266;
  background: #fff;
}

.query-actions {
  display: flex;
  align-items: center;
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

.tbl th,
.tbl td {
  border: 1px solid #ebeef5;
  padding: 10px;
  text-align: center;
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
  margin-top: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}

.pager-summary {
  color: #606266;
  font-size: 13px;
}

.pager-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
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
  color: #c0c4cc;
  cursor: not-allowed;
  border-color: #ebeef5;
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

.btn-primary,
.btn-secondary {
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

.btn-primary:hover:not(:disabled) {
  background: #66b1ff;
  border-color: #66b1ff;
}

.btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn-secondary:hover {
  color: #409eff;
  border-color: #c6e2ff;
  background: #ecf5ff;
}

.btn-compact {
  height: 32px;
  padding: 0 10px;
  font-size: 13px;
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
  width: min(100%, 600px);
  max-height: calc(100vh - 48px);
  overflow: auto;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.modal-head {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  padding: 16px 20px;
  border-bottom: 1px solid #ebeef5;
}

.modal-head h3 {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.modal-body {
  display: grid;
  gap: 12px;
  padding: 16px 20px 20px;
}

.section-card {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 12px;
  background: #fcfdff;
}

.section-card h4 {
  font-size: 14px;
  color: #303133;
  margin: 0 0 10px;
}

.section-with-icon > h4 {
  margin-bottom: 12px;
}

.basic-with-icon {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px 20px;
  align-items: start;
}

.basic-with-icon-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 14px;
}

.basic-with-icon-fields label {
  display: grid;
  gap: 6px;
}

.basic-with-icon-fields label span {
  font-size: 13px;
  color: #606266;
}

.basic-with-icon-fields label input {
  height: 36px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 0 10px;
  font-size: 13px;
  color: #303133;
}

.basic-with-icon-fields label input:disabled {
  background: #f5f7fa;
  color: #909399;
  cursor: not-allowed;
}

.basic-with-icon-side {
  width: 148px;
  padding: 10px 10px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.basic-icon-heading {
  font-size: 12px;
  font-weight: 600;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  margin-bottom: 8px;
}

.icon-upload-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: stretch;
  width: 100%;
}

.icon-file-hidden {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

.icon-preview {
  width: 100%;
  aspect-ratio: 1;
  max-height: 148px;
  padding: 0;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  background: #f5f7fa;
  cursor: pointer;
  display: grid;
  place-items: center;
  overflow: hidden;
  box-sizing: border-box;
}

.icon-preview:hover:not(:disabled) {
  border-color: #409eff;
  background: #ecf5ff;
}

.icon-preview:disabled {
  cursor: wait;
  opacity: 0.85;
}

.icon-preview-img {
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
}

.icon-placeholder-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px;
  text-align: center;
}

.icon-placeholder-title {
  font-size: 12px;
  color: #606266;
}

.icon-placeholder-sub {
  font-size: 11px;
  color: #c0c4cc;
}

.icon-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: stretch;
}

.icon-actions .btn-primary,
.icon-actions .btn-secondary {
  flex: 1 1 auto;
  min-width: 0;
}

.full {
  grid-column: 1 / -1;
}

textarea {
  width: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 13px;
  color: #303133;
  resize: vertical;
  box-sizing: border-box;
}

textarea:focus {
  outline: none;
  border-color: #409eff;
}

.actions {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  padding-top: 4px;
}

@media (max-width: 720px) {
  .basic-with-icon {
    grid-template-columns: 1fr;
  }

  .basic-with-icon-side {
    width: 140px;
    position: static;
  }

  .query-row {
    flex-direction: column;
    align-items: stretch;
  }

  .query-item {
    width: 100%;
    min-width: 0;
  }

  .keyword-input {
    width: 100%;
  }

  .basic-with-icon-fields {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 960px) {
  .pager {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
