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
const resonanceMagicStaticBase = (import.meta.env.VITE_STATIC_BASE_URL || 'https://wikiroco.com').replace(/\/+$/, '')

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
  const iconUrl = (form.icon_url || '').trim()
  if (iconUrl) return iconUrl
  const icon = (form.icon || '').trim()
  if (!icon) return ''
  if (icon.startsWith('http')) return icon
  if (icon.startsWith('/resonance-magic/') || icon.startsWith('resonance-magic/')) {
    const filename = icon.split('/').filter(Boolean).pop() || ''
    return filename ? `${resonanceMagicStaticBase}/images/resonance-magic/${filename}` : ''
  }
  return icon
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
      icon = result.url
      form.icon_url = result.url
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
    <section class="ops-card-padded">
      <div class="ops-filter-bar" style="margin-bottom:16px;">
        <div class="ops-form-item" style="min-width:200px;">
          <span class="ops-filter-label">关键字</span>
          <input v-model="keyword" class="ops-input" type="text" placeholder="共鸣魔法名称" @keyup.enter="search" />
        </div>
        <div class="ops-filter-actions">
          <button type="button" class="ops-btn ops-btn-primary" @click="search">查询</button>
          <button type="button" class="ops-btn ops-btn-secondary" @click="resetFilters">重置</button>
        </div>
      </div>
      <div class="ops-toolbar">
        <button v-if="isAdmin" type="button" class="ops-btn ops-btn-primary" @click="openCreateModal">新增共鸣魔法</button>
        <span class="ops-toolbar-meta">共 {{ total }} 条</span>
      </div>

      <p v-if="error" class="ops-error">{{ error }}</p>

      <div v-if="loading" class="ops-loading">加载中...</div>
      <div v-else-if="!items.length" class="ops-empty">暂无数据</div>
      <div v-else class="ops-table-wrap">
        <table class="ops-table">
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
        <span class="ops-pagination-summary">共 {{ total }} 条，当前显示 {{ pageStart }}-{{ pageEnd }} 条</span>
        <div class="ops-pagination-controls">
          <button type="button" class="ops-page-btn" :disabled="currentPage === 1" @click="goToPage(1)">首页</button>
          <button type="button" class="ops-page-btn" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">上一页</button>
          <button
            v-for="p in visiblePages"
            :key="p"
            type="button"
            class="ops-page-btn"
            :class="{ 'ops-page-btn--active': p === currentPage }"
            @click="goToPage(p)"
          >
            {{ p }}
          </button>
          <button type="button" class="ops-page-btn" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">下一页</button>
          <button type="button" class="ops-page-btn" :disabled="currentPage === totalPages" @click="goToPage(totalPages)">末页</button>
        </div>
      </div>
    </section>

    <div v-if="modalVisible" class="ops-modal-mask">
      <section class="ops-modal" @click.stop>
        <div class="ops-modal-header">
          <h3>{{ editingId ? '编辑共鸣魔法' : '新增共鸣魔法' }}</h3>
        </div>
        <form class="ops-modal-body" @submit.prevent="submit">
          <section style="border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);padding:12px;background:var(--ops-bg);">
            <h4 style="font-size:14px;color:var(--ops-text);margin:0 0 12px;">基础信息</h4>
            <div style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px 20px;align-items:start;">
              <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px 14px;">
                <label style="display:grid;gap:6px;">
                  <span style="font-size:13px;color:var(--ops-text-secondary);">名称</span>
                  <input v-model="form.name" class="ops-input" required type="text" placeholder="例：元素共鸣" maxlength="50" />
                </label>
                <label style="display:grid;gap:6px;">
                  <span style="font-size:13px;color:var(--ops-text-secondary);">可使用次数</span>
                  <input v-model.number="form.max_usage_count" class="ops-input" required type="number" min="1" placeholder="例：1" />
                </label>
                <label style="display:grid;gap:6px;">
                  <span style="font-size:13px;color:var(--ops-text-secondary);">排序</span>
                  <input v-model.number="form.sort_order" class="ops-input" type="number" placeholder="越小越靠前" />
                </label>
              </div>
              <aside style="width:148px;padding:10px 10px 12px;border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);background:var(--ops-surface);box-shadow:0 1px 2px rgba(0,0,0,0.04);">
                <div style="font-size:12px;font-weight:600;color:var(--ops-muted);text-transform:uppercase;letter-spacing:0.02em;margin-bottom:8px;">图标</div>
                <div style="display:flex;flex-direction:column;gap:8px;align-items:stretch;width:100%;">
                  <button
                    type="button"
                    style="width:100%;aspect-ratio:1;max-height:148px;padding:0;border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);background:var(--ops-bg);cursor:pointer;display:grid;place-items:center;overflow:hidden;"
                    :disabled="saving"
                    @click="triggerIconFilePick"
                  >
                    <img v-if="iconDisplaySrc" :src="iconDisplaySrc" alt="" style="max-width:100%;max-height:100%;object-fit:contain;" />
                    <div v-else style="display:flex;flex-direction:column;align-items:center;gap:4px;padding:8px;text-align:center;">
                      <span style="font-size:12px;color:var(--ops-text-secondary);">暂无</span>
                      <span style="font-size:11px;color:var(--ops-muted);">点击上传</span>
                    </div>
                  </button>
                  <input
                    ref="iconFileInputRef"
                    type="file"
                    style="position:absolute;width:0;height:0;opacity:0;pointer-events:none;"
                    accept=".webp,.png,.jpg,.jpeg,.gif,image/webp,image/png,image/jpeg,image/gif"
                    :disabled="saving"
                    @change="onIconImageSelected"
                  />
                  <div style="display:flex;flex-wrap:wrap;gap:6px;justify-content:stretch;">
                    <button type="button" class="ops-btn ops-btn-primary ops-btn-sm" style="flex:1;" :disabled="saving" @click="triggerIconFilePick">
                      {{ iconDisplaySrc ? '更换' : '选择图片' }}
                    </button>
                    <button
                      v-if="form.icon || pendingIconFile"
                      type="button"
                      class="ops-btn ops-btn-secondary ops-btn-sm"
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

          <section style="border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);padding:12px;background:var(--ops-bg);grid-column:1/-1;">
            <h4 style="font-size:14px;color:var(--ops-text);margin:0 0 10px;">描述</h4>
            <textarea v-model="form.description" class="ops-input" style="height:auto;min-height:96px;padding:8px 12px;resize:vertical;" rows="4" placeholder="请输入共鸣魔法描述"></textarea>
          </section>

          <div class="ops-modal-footer">
            <button type="submit" class="ops-btn ops-btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
            <button type="button" class="ops-btn ops-btn-secondary" @click="closeModal">取消</button>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>
