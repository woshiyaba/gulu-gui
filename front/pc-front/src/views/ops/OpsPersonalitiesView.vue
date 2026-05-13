<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  clearOpsToken,
  createOpsPersonality,
  deleteOpsPersonality,
  fetchOpsDicts,
  fetchOpsMe,
  fetchOpsPersonalities,
  showOpsToast,
  updateOpsPersonality,
  type OpsPersonalityItem,
  type OpsPersonalityStat,
} from '@/api/ops'

const STAT_KEYS: OpsPersonalityStat[] = ['hp', 'phy_atk', 'mag_atk', 'phy_def', 'mag_def', 'spd']
const STAT_DICT_TYPE = 'pokemon_stat'
const DEFAULT_STAT_LABELS: Record<OpsPersonalityStat, string> = {
  hp: 'HP',
  phy_atk: '物攻',
  mag_atk: '魔攻',
  phy_def: '物防',
  mag_def: '魔防',
  spd: '速度',
}
const STAT_COL_MAP: Record<OpsPersonalityStat, keyof OpsPersonalityItem> = {
  hp: 'hp_mod_pct',
  phy_atk: 'phy_atk_mod_pct',
  mag_atk: 'mag_atk_mod_pct',
  phy_def: 'phy_def_mod_pct',
  mag_def: 'mag_def_mod_pct',
  spd: 'spd_mod_pct',
}

const statLabels = ref<Record<OpsPersonalityStat, string>>({ ...DEFAULT_STAT_LABELS })
const statOrder = ref<OpsPersonalityStat[]>([...STAT_KEYS])

function labelOf(key: OpsPersonalityStat): string {
  return statLabels.value[key] || DEFAULT_STAT_LABELS[key]
}

async function loadStatDict() {
  try {
    const resp = await fetchOpsDicts({ dict_type: STAT_DICT_TYPE, page: 1, page_size: 100 })
    const validKeys = new Set<string>(STAT_KEYS)
    const labels = { ...DEFAULT_STAT_LABELS }
    const ordered = [...resp.items]
      .filter((d) => validKeys.has(d.code))
      .sort((a, b) => a.sort_order - b.sort_order)
    const orderKeys: OpsPersonalityStat[] = []
    for (const d of ordered) {
      const key = d.code as OpsPersonalityStat
      if (d.label) labels[key] = d.label
      orderKeys.push(key)
    }
    for (const k of STAT_KEYS) {
      if (!orderKeys.includes(k)) orderKeys.push(k)
    }
    statLabels.value = labels
    statOrder.value = orderKeys
  } catch {
    // 忽略
  }
}

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const items = ref<OpsPersonalityItem[]>([])
const total = ref(0)
const isAdmin = ref(false)

const currentPage = ref(1)
const pageSize = 10
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

async function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  await loadData()
}

const query = reactive({
  keyword: '',
  buff_stat: '' as '' | OpsPersonalityStat,
  nerf_stat: '' as '' | OpsPersonalityStat,
})

const drawerVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  id: null as number | null,
  name: '',
  buff_stat: '' as '' | OpsPersonalityStat,
  nerf_stat: '' as '' | OpsPersonalityStat,
})

function statValueOf(item: OpsPersonalityItem, key: OpsPersonalityStat): number {
  return Number(item[STAT_COL_MAP[key]] ?? 0)
}

function formatMod(value: number): string {
  const v = Number(value) || 0
  if (v > 0) return `+${Math.round(v * 100)}%`
  if (v < 0) return `${Math.round(v * 100)}%`
  return '—'
}

function modClass(value: number): string {
  const v = Number(value) || 0
  if (v > 0) return 'mod-buff'
  if (v < 0) return 'mod-nerf'
  return 'mod-zero'
}

const formValid = computed(() => {
  if (!form.name.trim()) return false
  const { buff_stat, nerf_stat } = form
  if (!buff_stat && !nerf_stat) return true
  if (buff_stat && nerf_stat && buff_stat !== nerf_stat) return true
  return false
})

function resetForm() {
  editingId.value = null
  form.id = null
  form.name = ''
  form.buff_stat = ''
  form.nerf_stat = ''
}

function openCreateDrawer() {
  resetForm()
  drawerVisible.value = true
}

function closeDrawer() {
  drawerVisible.value = false
}

function editItem(item: OpsPersonalityItem) {
  editingId.value = item.id
  form.id = item.id
  form.name = item.name
  form.buff_stat = (item.buff_stat ?? '') as '' | OpsPersonalityStat
  form.nerf_stat = (item.nerf_stat ?? '') as '' | OpsPersonalityStat
  drawerVisible.value = true
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [me, data] = await Promise.all([
      fetchOpsMe(),
      fetchOpsPersonalities({
        keyword: query.keyword.trim(),
        buff_stat: query.buff_stat,
        nerf_stat: query.nerf_stat,
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

async function submitForm() {
  if (saving.value) return
  if (!formValid.value) {
    error.value = '请校验：名称必填，且加成项与削弱项须不同（或都不选表示中性）。'
    showOpsToast(error.value, 'error')
    return
  }
  saving.value = true
  error.value = ''
  try {
    const mods: Record<string, number> = {
      hp_mod_pct: 0,
      phy_atk_mod_pct: 0,
      mag_atk_mod_pct: 0,
      phy_def_mod_pct: 0,
      mag_def_mod_pct: 0,
      spd_mod_pct: 0,
    }
    if (form.buff_stat) mods[STAT_COL_MAP[form.buff_stat]] = 0.1
    if (form.nerf_stat) mods[STAT_COL_MAP[form.nerf_stat]] = -0.1
    const payload = {
      id: editingId.value ? undefined : form.id,
      name: form.name.trim(),
      ...mods,
    } as any
    if (editingId.value) {
      await updateOpsPersonality(editingId.value, payload)
      showOpsToast('性格已更新', 'success')
    } else {
      await createOpsPersonality(payload)
      showOpsToast('性格已创建', 'success')
    }
    closeDrawer()
    await loadData()
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '保存失败'
    showOpsToast(error.value, 'error')
  } finally {
    saving.value = false
  }
}

async function removeItem(item: OpsPersonalityItem) {
  if (!isAdmin.value) return
  if (!window.confirm(`确定删除性格「${item.name}」吗？`)) return
  try {
    await deleteOpsPersonality(item.id)
    if (editingId.value === item.id) resetForm()
    await loadData()
    showOpsToast('性格已删除', 'success')
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '删除失败'
    showOpsToast(error.value, 'error')
  }
}

function onSearch() {
  currentPage.value = 1
  void loadData()
}

function onResetFilter() {
  query.keyword = ''
  query.buff_stat = ''
  query.nerf_stat = ''
  currentPage.value = 1
  void loadData()
}

onMounted(() => {
  void loadStatDict()
  void loadData()
})
</script>

<template>
  <div class="ops-page">
    <section class="ops-card-padded">
      <div class="ops-filter-bar">
        <div class="ops-filter-item">
          <span class="ops-filter-label">关键字</span>
          <input v-model="query.keyword" class="ops-input" style="width:180px" type="text" placeholder="名称" @keyup.enter="onSearch" />
        </div>
        <div class="ops-filter-item">
          <span class="ops-filter-label">加成项</span>
          <select v-model="query.buff_stat" class="ops-select" style="width:120px">
            <option value="">全部</option>
            <option v-for="key in statOrder" :key="`buff-${key}`" :value="key">{{ labelOf(key) }}</option>
          </select>
        </div>
        <div class="ops-filter-item">
          <span class="ops-filter-label">削弱项</span>
          <select v-model="query.nerf_stat" class="ops-select" style="width:120px">
            <option value="">全部</option>
            <option v-for="key in statOrder" :key="`nerf-${key}`" :value="key">{{ labelOf(key) }}</option>
          </select>
        </div>
        <div class="ops-filter-actions">
          <button type="button" class="ops-btn ops-btn-primary" @click="onSearch">查询</button>
          <button type="button" class="ops-btn ops-btn-secondary" @click="onResetFilter">重置</button>
        </div>
      </div>

      <div class="ops-toolbar">
        <div class="ops-toolbar-left">
          <button v-if="isAdmin" type="button" class="ops-btn ops-btn-primary" @click="openCreateDrawer">新增</button>
        </div>
        <span class="ops-toolbar-meta">共 {{ total }} 条</span>
      </div>

      <p v-if="error" class="ops-error">{{ error }}</p>
      <div v-if="loading" class="ops-loading">加载中...</div>
      <div v-else-if="!items.length" class="ops-empty"><strong>暂无数据</strong></div>
      <div v-else class="ops-table-wrap">
        <table class="ops-table">
          <thead>
            <tr>
              <th>名称</th>
              <th>加成项</th>
              <th>削弱项</th>
              <th v-for="key in statOrder" :key="`th-${key}`">{{ labelOf(key) }}</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td style="font-weight:500;">{{ item.name }}</td>
              <td><span v-if="item.buff_stat" class="ops-badge ops-badge--success" style="border-radius:4px;">{{ labelOf(item.buff_stat) }}</span><span v-else style="color:var(--ops-text-secondary)">—</span></td>
              <td><span v-if="item.nerf_stat" class="ops-badge ops-badge--danger" style="border-radius:4px;">{{ labelOf(item.nerf_stat) }}</span><span v-else style="color:var(--ops-text-secondary)">—</span></td>
              <td v-for="key in statOrder" :key="`td-${item.id}-${key}`" :style="{ color: statValueOf(item, key) > 0 ? 'var(--ops-success)' : statValueOf(item, key) < 0 ? 'var(--ops-danger)' : 'var(--ops-muted)' }">
                {{ formatMod(statValueOf(item, key)) }}
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
          <button v-for="page in visiblePages" :key="page" type="button" class="ops-page-btn" :class="{ 'ops-page-btn--active': page === currentPage }" @click="goToPage(page)">{{ page }}</button>
          <button type="button" class="ops-page-btn" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">下一页</button>
          <button type="button" class="ops-page-btn" :disabled="currentPage === totalPages" @click="goToPage(totalPages)">末页</button>
        </div>
      </div>
    </section>

    <div v-if="drawerVisible" class="ops-modal-mask" @click="closeDrawer">
      <section class="ops-modal" @click.stop>
        <div class="ops-modal-header">
          <h3>{{ editingId ? '编辑性格' : '新增性格' }}</h3>
          <button type="button" class="ops-modal-close" @click="closeDrawer">✕</button>
        </div>
        <form class="ops-modal-body" @submit.prevent="submitForm">
          <div class="ops-form-grid" style="grid-template-columns:repeat(2,1fr);">
            <div class="ops-form-item">
              <label>名称</label>
              <input v-model="form.name" class="ops-input" type="text" required placeholder="例：胆小" maxlength="32" />
            </div>
            <div class="ops-form-item">
              <label>加成项</label>
              <select v-model="form.buff_stat" class="ops-select">
                <option value="">无（中性）</option>
                <option v-for="key in statOrder" :key="`buff-opt-${key}`" :value="key" :disabled="form.nerf_stat === key">{{ labelOf(key) }}</option>
              </select>
            </div>
            <div class="ops-form-item">
              <label>削弱项</label>
              <select v-model="form.nerf_stat" class="ops-select">
                <option value="">无（中性）</option>
                <option v-for="key in statOrder" :key="`nerf-opt-${key}`" :value="key" :disabled="form.buff_stat === key">{{ labelOf(key) }}</option>
              </select>
            </div>
          </div>
          <div class="ops-modal-footer">
            <button type="submit" class="ops-btn ops-btn-primary" :disabled="saving || !formValid">{{ saving ? '保存中...' : '保存' }}</button>
            <button type="button" class="ops-btn ops-btn-secondary" @click="closeDrawer">取消</button>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>
