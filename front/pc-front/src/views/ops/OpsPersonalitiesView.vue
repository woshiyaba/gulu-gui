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

// 六维 label 从 sys_dict(dict_type='pokemon_stat') 动态加载，
// 字典缺失时回退到内置默认值。
const statLabels = ref<Record<OpsPersonalityStat, string>>({ ...DEFAULT_STAT_LABELS })
// 下拉顺序跟随字典 sort_order；字典未就绪时使用 STAT_KEYS 原序。
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
    // 把字典里没有的 key 补到末尾，保证六项都显示
    for (const k of STAT_KEYS) {
      if (!orderKeys.includes(k)) orderKeys.push(k)
    }
    statLabels.value = labels
    statOrder.value = orderKeys
  } catch {
    // 忽略：沿用默认 label 和顺序
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
  // 允许全中性，或一加一减（且不同项）
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
    <section class="table-card">
      <div class="filter-bar">
        <label class="filter-item">
          <span>关键字</span>
          <input v-model="query.keyword" type="text" placeholder="名称" @keyup.enter="onSearch" />
        </label>
        <label class="filter-item">
          <span>加成项</span>
          <select v-model="query.buff_stat">
            <option value="">全部</option>
            <option v-for="key in statOrder" :key="`buff-${key}`" :value="key">{{ labelOf(key) }}</option>
          </select>
        </label>
        <label class="filter-item">
          <span>削弱项</span>
          <select v-model="query.nerf_stat">
            <option value="">全部</option>
            <option v-for="key in statOrder" :key="`nerf-${key}`" :value="key">{{ labelOf(key) }}</option>
          </select>
        </label>
        <div class="filter-actions">
          <button type="button" class="btn-primary" @click="onSearch">查询</button>
          <button type="button" class="btn-secondary" @click="onResetFilter">重置</button>
        </div>
      </div>

      <div class="toolbar">
        <div class="toolbar-left">
          <button v-if="isAdmin" type="button" class="btn-primary" @click="openCreateDrawer">新增</button>
        </div>
        <div class="toolbar-meta">共 {{ total }} 条</div>
      </div>

      <p v-if="error" class="error">{{ error }}</p>

      <div v-if="loading" class="table-placeholder muted">加载中...</div>
      <div v-else-if="!items.length" class="table-placeholder">
        <strong>暂无数据</strong>
        <span>点击「新增」或「从 JSON 重置」初始化数据。</span>
      </div>
      <div v-else class="table-wrap">
        <table class="tbl">
          <thead>
            <tr>
              <th>名称</th>
              <th>加成项</th>
              <th>削弱项</th>
              <th v-for="key in statOrder" :key="`th-${key}`">{{ labelOf(key) }}</th>
              <th class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="cell-name">{{ item.name }}</td>
              <td>
                <span v-if="item.buff_stat" class="tag mod-buff">{{ labelOf(item.buff_stat) }}</span>
                <span v-else class="muted">—</span>
              </td>
              <td>
                <span v-if="item.nerf_stat" class="tag mod-nerf">{{ labelOf(item.nerf_stat) }}</span>
                <span v-else class="muted">—</span>
              </td>
              <td v-for="key in statOrder" :key="`td-${item.id}-${key}`" :class="modClass(statValueOf(item, key))">
                {{ formatMod(statValueOf(item, key)) }}
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
          <h2>{{ editingId ? '编辑性格' : '新增性格' }}</h2>
          <button type="button" class="modal-close" @click="closeDrawer">关闭</button>
        </div>

        <form class="modal-body" @submit.prevent="submitForm">
          <div class="form-grid">
            <label class="form-row">
              <span>名称</span>
              <input v-model="form.name" type="text" required placeholder="例：胆小" maxlength="32" />
            </label>
            <label class="form-row">
              <span>加成项</span>
              <select v-model="form.buff_stat">
                <option value="">无（中性）</option>
                <option
                  v-for="key in statOrder"
                  :key="`buff-opt-${key}`"
                  :value="key"
                  :disabled="form.nerf_stat === key"
                >{{ labelOf(key) }}</option>
              </select>
            </label>
            <label class="form-row">
              <span>削弱项</span>
              <select v-model="form.nerf_stat">
                <option value="">无（中性）</option>
                <option
                  v-for="key in statOrder"
                  :key="`nerf-opt-${key}`"
                  :value="key"
                  :disabled="form.buff_stat === key"
                >{{ labelOf(key) }}</option>
              </select>
            </label>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn-secondary" @click="closeDrawer">取消</button>
            <button type="submit" class="btn-primary" :disabled="saving || !formValid">
              {{ saving ? '保存中...' : '保存' }}
            </button>
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

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px;
  margin-bottom: 12px;
}

.filter-item {
  display: grid;
  gap: 4px;
  min-width: 160px;
}

.filter-item span {
  font-size: 12px;
  color: #606266;
}

.filter-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.toolbar-left {
  display: flex;
  gap: 10px;
}

.toolbar-meta {
  font-size: 13px;
  color: #909399;
}

.btn-primary,
.btn-secondary {
  height: 32px;
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

.btn-primary:hover:not(:disabled) {
  background: #66b1ff;
  border-color: #66b1ff;
}

.btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
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
  padding: 10px 12px;
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

.col-actions {
  width: 120px;
}

.cell-name {
  font-weight: 600;
  color: #303133;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  line-height: 1.5;
}

.mod-buff {
  color: #67c23a;
  background: rgba(103, 194, 58, 0.12);
}

.mod-nerf {
  color: #f56c6c;
  background: rgba(245, 108, 108, 0.12);
}

.mod-zero {
  color: #909399;
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
  min-height: 200px;
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
  height: 32px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #fff;
  color: #303133;
  padding: 0 12px;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
  font-size: 13px;
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
  width: min(100%, 520px);
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
  padding: 16px 20px;
  border-bottom: 1px solid #ebeef5;
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
  padding: 16px 20px 20px;
  overflow: auto;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px 16px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.form-row > span {
  color: #606266;
  font-size: 12px;
  line-height: 1;
}

.form-row input,
.form-row select {
  width: 100%;
  height: 32px;
  padding: 0 10px;
  font-size: 13px;
  color: #303133;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 3px;
  box-sizing: border-box;
  transition: border-color 0.15s ease;
}

.form-row input:focus,
.form-row select:focus {
  outline: none;
  border-color: #409eff;
}

.form-row input:disabled {
  background: #f5f7fa;
  color: #909399;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

@media (max-width: 540px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .modal {
    width: 100%;
  }
}
</style>
