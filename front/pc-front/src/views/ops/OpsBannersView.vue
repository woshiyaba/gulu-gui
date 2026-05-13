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
    <section class="ops-card-padded">
      <div class="ops-toolbar">
        <button type="button" class="ops-btn ops-btn-primary" @click="openCreateDrawer">新增</button>
        <span class="ops-toolbar-meta">共 {{ total }} 条</span>
      </div>

      <p v-if="error" class="ops-error">{{ error }}</p>

      <div v-if="loading" class="ops-loading">加载中...</div>
      <div v-else-if="!items.length" class="ops-empty">
        <strong>暂无数据</strong>
        <span>点击「新增」添加 Banner。</span>
      </div>
      <div v-else class="ops-table-wrap">
        <table class="ops-table">
          <thead>
            <tr>
              <th class="ops-col-index">序号</th>
              <th>标题</th>
              <th>图片预览</th>
              <th>跳转类型</th>
              <th>跳转阵容</th>
              <th class="ops-col-sort">排序</th>
              <th>状态</th>
              <th class="ops-col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td>{{ item.title }}</td>
              <td>
                <img v-if="item.image_url" :src="item.image_url" style="max-width:120px;max-height:48px;border-radius:4px;object-fit:cover;" />
                <span v-else style="color:var(--ops-muted);">无</span>
              </td>
              <td>{{ linkTypeLabel(item.link_type) }}</td>
              <td>{{ linkParamLabel(item) }}</td>
              <td>{{ item.sort_order }}</td>
              <td>
                <span class="ops-badge" :class="item.is_active ? 'ops-badge--success' : 'ops-badge--default'">
                  {{ item.is_active ? '启用' : '禁用' }}
                </span>
              </td>
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

    <div v-if="drawerVisible" class="ops-modal-mask" @click="closeDrawer">
      <section class="ops-modal" @click.stop>
        <div class="ops-modal-header">
          <h3>{{ editingId ? '编辑Banner' : '新增Banner' }}</h3>
          <button type="button" class="ops-modal-close" @click="closeDrawer">✕</button>
        </div>

        <form class="ops-modal-body" @submit.prevent="submitForm">
          <div class="ops-form-grid">
            <label class="ops-form-row">
              <span>标题</span>
              <input v-model="form.title" class="ops-input" type="text" placeholder="Banner标题" />
            </label>
            <label class="ops-form-row">
              <span>图片URL</span>
              <input v-model="form.image_url" class="ops-input" required type="text" placeholder="Banner图片地址" />
            </label>
            <label class="ops-form-row">
              <span>跳转类型</span>
              <select v-model="form.link_type" class="ops-select">
                <option value="">不跳转</option>
                <option v-for="opt in lineupTypeOptions" :key="opt.code" :value="opt.code">
                  {{ opt.label }}
                </option>
              </select>
            </label>
            <label class="ops-form-row">
              <span>排序</span>
              <input v-model="form.sort_order" class="ops-input" type="number" placeholder="排序值" />
            </label>
            <label class="ops-form-row">
              <span>状态</span>
              <select v-model="form.is_active" class="ops-select">
                <option :value="true">启用</option>
                <option :value="false">禁用</option>
              </select>
            </label>
          </div>

          <!-- 阵容选择区域 -->
          <div v-if="hasLinkType" style="margin-top:18px;border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);padding:14px;">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
              <span style="font-size:13px;font-weight:600;color:var(--ops-text);">
                选择阵容{{ isMultiMode ? '（可多选）' : '' }}
              </span>
              <span v-if="selectedLineupIds.length > 0" style="font-size:12px;color:var(--ops-accent);">
                已选 {{ selectedLineupIds.length }} 条
              </span>
            </div>

            <div v-if="lineupLoading" style="text-align:center;padding:16px 0;color:var(--ops-muted);font-size:13px;">加载阵容中...</div>
            <div v-else-if="lineupOptions.length === 0" style="text-align:center;padding:16px 0;color:var(--ops-muted);font-size:13px;">
              该类型暂无阵容数据
            </div>
            <div v-else style="max-height:240px;overflow:auto;display:flex;flex-direction:column;gap:4px;">
              <div
                v-for="lineup in lineupOptions"
                :key="lineup.id"
                :style="{
                  display:'flex',alignItems:'center',gap:'8px',padding:'8px 12px',borderRadius:'4px',cursor:'pointer',
                  background: isLineupSelected(lineup.id) ? 'var(--ops-accent-light)' : 'transparent',
                  border: isLineupSelected(lineup.id) ? '1px solid var(--ops-accent)' : '1px solid transparent',
                }"
                @click="toggleLineupSelection(lineup.id)"
              >
                <span :style="{
                  width:'18px',height:'18px',border:'1px solid var(--ops-border)',borderRadius:'3px',
                  display:'flex',alignItems:'center',justifyContent:'center',fontSize:'12px',
                  background: isLineupSelected(lineup.id) ? 'var(--ops-accent)' : 'transparent',
                  borderColor: isLineupSelected(lineup.id) ? 'var(--ops-accent)' : 'var(--ops-border)',
                  color: isLineupSelected(lineup.id) ? '#fff' : 'transparent',
                  flexShrink:0,
                }">{{ isLineupSelected(lineup.id) ? '✓' : '' }}</span>
                <span style="font-size:13px;color:var(--ops-text);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ lineup.title || `阵容#${lineup.id}` }}</span>
                <span style="font-size:12px;color:var(--ops-muted);flex-shrink:0;">
                  {{ lineup.member_count }}只 · 排序{{ lineup.sort_order }}
                  <template v-if="!lineup.is_active"> · 已禁用</template>
                </span>
              </div>
            </div>
          </div>

          <div v-if="form.image_url" style="margin-top:18px;">
            <span style="display:block;font-size:13px;color:var(--ops-text-secondary);margin-bottom:8px;">图片预览</span>
            <img :src="form.image_url" style="max-width:100%;max-height:200px;border-radius:4px;border:1px solid var(--ops-border);" />
          </div>
          <div class="ops-modal-footer" style="margin-top:20px;">
            <button type="submit" class="ops-btn ops-btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
            <button type="button" class="ops-btn ops-btn-secondary" @click="closeDrawer">取消</button>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>
