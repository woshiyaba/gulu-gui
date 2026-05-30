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
        form.icon = data.url
        form.icon_url = data.url
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
    <section class="ops-card-padded">
      <div class="ops-filter-bar" style="align-items:flex-end;flex-wrap:wrap;margin-bottom:16px;">
        <label class="ops-form-item" style="min-width:200px;">
          <span class="ops-filter-label">技能名称</span>
          <input v-model="keyword" class="ops-input" type="text" placeholder="请输入技能名称" />
        </label>
        <label class="ops-form-item" style="min-width:160px;">
          <span class="ops-filter-label">属性</span>
          <select v-model="attr" class="ops-select">
            <option value="">全部</option>
            <option v-for="opt in attrOptions" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </label>
        <label class="ops-form-item" style="min-width:160px;">
          <span class="ops-filter-label">类型</span>
          <select v-model="type" class="ops-select">
            <option value="">全部</option>
            <option v-for="opt in typeOptions" :key="opt" :value="opt">{{ opt }}</option>
          </select>
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
        <span>请调整筛选条件后重试，或新增技能。</span>
      </div>
      <div v-else class="ops-table-wrap">
        <table class="ops-table">
          <thead>
            <tr>
              <th style="width:80px;">序号</th>
              <th style="width:72px;">图标</th>
              <th>技能名称</th>
              <th>属性</th>
              <th>类型</th>
              <th style="width:80px;">威力</th>
              <th style="width:80px;">消耗</th>
              <th style="max-width:260px;">描述</th>
              <th style="width:200px;">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td>
                <img v-if="item.icon_url" :src="item.icon_url" style="width:36px;height:36px;object-fit:contain;vertical-align:middle;" alt="" />
                <span v-else style="color:var(--ops-muted);">-</span>
              </td>
              <td style="min-width:140px;font-weight:500;">{{ item.name }}</td>
              <td>{{ item.attr || '-' }}</td>
              <td>{{ item.type || '-' }}</td>
              <td>{{ item.power }}</td>
              <td>{{ item.consume }}</td>
              <td style="max-width:260px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" :title="item.skill_desc">{{ item.skill_desc || '-' }}</td>
              <td>
                <div class="ops-action-group">
                  <button type="button" class="ops-btn ops-btn-text" @click="editItem(item)">修改</button>
                  <button type="button" class="ops-btn ops-btn-text" @click="openUsages(item)">占用</button>
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
          <h3>{{ editingId ? '编辑技能' : '新增技能' }}</h3>
          <button type="button" class="ops-modal-close" @click="closeDrawer">✕</button>
        </div>

        <form class="ops-modal-body" @submit.prevent="submitForm">
          <div class="ops-form-grid">
            <label class="ops-form-row">
              <span>技能名称</span>
              <input v-model="form.name" class="ops-input" required type="text" maxlength="50" placeholder="请输入技能名称" />
            </label>
            <label class="ops-form-row">
              <span>属性</span>
              <select v-model="form.attr" class="ops-select">
                <option value="">请选择</option>
                <option v-for="opt in attrOptions" :key="opt" :value="opt">{{ opt }}</option>
              </select>
            </label>
            <label class="ops-form-row">
              <span>类型</span>
              <select v-model="form.type" class="ops-select">
                <option value="">请选择</option>
                <option v-for="opt in typeOptions" :key="opt" :value="opt">{{ opt }}</option>
              </select>
            </label>
            <label class="ops-form-row">
              <span>威力</span>
              <input v-model.number="form.power" class="ops-input" type="number" min="0" max="9999" />
            </label>
            <label class="ops-form-row">
              <span>消耗</span>
              <input v-model.number="form.consume" class="ops-input" type="number" min="0" max="9999" />
            </label>
            <label class="ops-form-row ops-form-grid-full" style="align-items:flex-start;">
              <span>描述</span>
              <textarea v-model="form.skill_desc" class="ops-input" style="height:auto;min-height:72px;padding:8px 12px;resize:vertical;" rows="3" placeholder="技能描述"></textarea>
            </label>
            <div class="ops-form-row ops-form-grid-full" style="align-items:flex-start;">
              <span>图标</span>
              <div style="display:flex;gap:14px;align-items:center;">
                <div style="width:72px;height:72px;border:1px dashed var(--ops-border);border-radius:var(--ops-radius-sm);display:grid;place-items:center;background:var(--ops-bg);overflow:hidden;">
                  <img v-if="iconDisplaySrc" :src="iconDisplaySrc" alt="" style="max-width:100%;max-height:100%;object-fit:contain;" />
                  <span v-else style="color:var(--ops-muted);font-size:12px;">无图标</span>
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
                  <input
                    ref="iconFileInputRef"
                    type="file"
                    accept="image/*"
                    style="display:none"
                    @change="onIconFileSelected"
                  />
                  <button type="button" class="ops-btn ops-btn-secondary ops-btn-sm" @click="iconFileInputRef?.click()">选择图标</button>
                  <button type="button" class="ops-btn ops-btn-secondary ops-btn-sm" @click="clearIcon">清除</button>
                  <span style="font-size:12px;color:var(--ops-muted);">点击保存时上传</span>
                </div>
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

    <div v-if="usagesVisible" class="ops-modal-mask">
      <section class="ops-modal" @click.stop>
        <div class="ops-modal-header">
          <h3>技能占用 - {{ usagesTarget?.name }}</h3>
          <button type="button" class="ops-modal-close" @click="closeUsages">✕</button>
        </div>
        <div class="ops-modal-body">
          <div v-if="usagesLoading" style="color:var(--ops-muted);">加载中...</div>
          <div v-else-if="!usages.length" style="color:var(--ops-muted);">该技能暂未被任何精灵使用</div>
          <table v-else class="ops-table">
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
