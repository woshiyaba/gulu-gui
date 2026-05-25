<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  clearOpsToken,
  createOpsEggHatchPet,
  deleteOpsEggHatchPet,
  fetchOpsEggHatchAvailablePokemon,
  fetchOpsEggHatchPetDetail,
  fetchOpsEggHatchPets,
  fetchOpsMe,
  showOpsToast,
  updateOpsEggHatchPet,
  type OpsEggHatchPetAvailablePokemon,
  type OpsEggHatchPetItem,
} from '@/api/ops'

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const keyword = ref('')
const leaderFilter = ref('') // '' | 'true' | 'false'
const items = ref<OpsEggHatchPetItem[]>([])
const editingId = ref<number | null>(null)
const drawerVisible = ref(false)
const currentPage = ref(1)
const pageSize = 10
const total = ref(0)

const form = reactive({
  pokemon_id: 0 as number,
  is_leader_form: false,
  hatch_data: 0,
  weight_low: 0,
  weight_high: 0,
  height_low: 0,
  height_high: 0,
})

const selectedPokemon = ref<OpsEggHatchPetAvailablePokemon | null>(null)
const availableSearch = ref('')
const availableLoading = ref(false)
const availablePokemon = ref<OpsEggHatchPetAvailablePokemon[]>([])
let availableTimer: number | null = null

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const pageStart = computed(() => (total.value === 0 ? 0 : (currentPage.value - 1) * pageSize + 1))
const pageEnd = computed(() => Math.min(currentPage.value * pageSize, total.value))
const visiblePages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  for (let p = start; p <= end; p += 1) pages.push(p)
  return pages
})

function resetForm() {
  editingId.value = null
  form.pokemon_id = 0
  form.is_leader_form = false
  form.hatch_data = 0
  form.weight_low = 0
  form.weight_high = 0
  form.height_low = 0
  form.height_high = 0
  selectedPokemon.value = null
  availableSearch.value = ''
  availablePokemon.value = []
}

function openCreateDrawer() {
  resetForm()
  drawerVisible.value = true
  void loadAvailablePokemon()
}

function closeDrawer() {
  drawerVisible.value = false
}

async function editItem(item: OpsEggHatchPetItem) {
  try {
    const detail = await fetchOpsEggHatchPetDetail(item.id)
    editingId.value = detail.id
    form.pokemon_id = detail.pokemon_id
    form.is_leader_form = detail.is_leader_form
    form.hatch_data = detail.hatch_data
    form.weight_low = detail.weight_low
    form.weight_high = detail.weight_high
    form.height_low = detail.height_low
    form.height_high = detail.height_high
    selectedPokemon.value = {
      id: detail.pokemon_id,
      no: detail.pokemon_no,
      name: detail.pokemon_name,
      image: detail.pokemon_image,
    }
    drawerVisible.value = true
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '加载失败', 'error')
  }
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [me, resp] = await Promise.all([
      fetchOpsMe(),
      fetchOpsEggHatchPets({
        keyword: keyword.value.trim() || undefined,
        is_leader_form: leaderFilter.value === '' ? undefined : leaderFilter.value === 'true',
        page: currentPage.value,
        page_size: pageSize,
      }),
    ])
    void me
    items.value = resp.items
    total.value = resp.total
    currentPage.value = resp.page
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
  leaderFilter.value = ''
  currentPage.value = 1
  await loadData()
}

async function loadAvailablePokemon() {
  availableLoading.value = true
  try {
    const resp = await fetchOpsEggHatchAvailablePokemon({
      keyword: availableSearch.value.trim() || undefined,
      limit: 30,
    })
    availablePokemon.value = resp.items
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '加载宠物失败', 'error')
  } finally {
    availableLoading.value = false
  }
}

watch(availableSearch, () => {
  if (editingId.value) return
  if (availableTimer) window.clearTimeout(availableTimer)
  availableTimer = window.setTimeout(() => {
    void loadAvailablePokemon()
  }, 250)
})

function pickAvailablePokemon(pokemon: OpsEggHatchPetAvailablePokemon) {
  selectedPokemon.value = pokemon
  form.pokemon_id = pokemon.id
}

async function submitForm() {
  if (saving.value) return
  saving.value = true
  error.value = ''
  try {
    if (!editingId.value && !form.pokemon_id) {
      showOpsToast('请选择宠物', 'error')
      return
    }
    if (form.weight_high < form.weight_low) {
      showOpsToast('体重上限不能小于下限', 'error')
      return
    }
    if (form.height_high < form.height_low) {
      showOpsToast('身高上限不能小于下限', 'error')
      return
    }
    const payload = {
      is_leader_form: form.is_leader_form,
      hatch_data: Number(form.hatch_data) || 0,
      weight_low: Number(form.weight_low) || 0,
      weight_high: Number(form.weight_high) || 0,
      height_low: Number(form.height_low) || 0,
      height_high: Number(form.height_high) || 0,
    }
    if (editingId.value) {
      await updateOpsEggHatchPet(editingId.value, payload)
      showOpsToast('孵化宠物已更新', 'success')
    } else {
      await createOpsEggHatchPet({ pokemon_id: form.pokemon_id, ...payload })
      showOpsToast('孵化宠物已创建', 'success')
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

async function removeItem(item: OpsEggHatchPetItem) {
  if (!window.confirm(`确定删除「${item.pokemon_name}」的孵化配置吗？`)) return
  try {
    await deleteOpsEggHatchPet(item.id)
    if (editingId.value === item.id) resetForm()
    await loadData()
    showOpsToast('孵化宠物已删除', 'success')
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '删除失败', 'error')
  }
}

onMounted(() => {
  void loadData()
})
</script>

<template>
  <div class="ops-page">
    <section class="ops-card-padded">
      <div class="ops-filter-bar" style="align-items:flex-end;flex-wrap:wrap;margin-bottom:16px;">
        <label class="ops-form-item" style="min-width:220px;">
          <span class="ops-filter-label">宠物名称 / 编号</span>
          <input v-model="keyword" class="ops-input" type="text" placeholder="请输入宠物名称或编号" />
        </label>
        <label class="ops-form-item" style="min-width:160px;">
          <span class="ops-filter-label">是否首领</span>
          <select v-model="leaderFilter" class="ops-select">
            <option value="">全部</option>
            <option value="true">首领形态</option>
            <option value="false">普通形态</option>
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
        <span>请调整筛选条件后重试，或新增孵化宠物。</span>
      </div>
      <div v-else class="ops-table-wrap">
        <table class="ops-table">
          <thead>
            <tr>
              <th style="width:80px;">序号</th>
              <th style="width:72px;">图鉴</th>
              <th style="width:90px;">编号</th>
              <th>宠物名称</th>
              <th style="width:96px;">是否首领</th>
              <th style="width:110px;">孵化时间(秒)</th>
              <th style="width:150px;">体重区间(g)</th>
              <th style="width:150px;">身高区间(cm)</th>
              <th style="width:160px;">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td>
                <img v-if="item.pokemon_image" :src="item.pokemon_image" style="width:36px;height:36px;object-fit:contain;vertical-align:middle;" alt="" />
                <span v-else style="color:var(--ops-muted);">-</span>
              </td>
              <td>{{ item.pokemon_no || '-' }}</td>
              <td>{{ item.pokemon_name }}</td>
              <td>
                <span class="ops-badge" :class="item.is_leader_form ? 'ops-badge--accent' : 'ops-badge--default'">{{ item.is_leader_form ? '首领' : '否' }}</span>
              </td>
              <td>{{ item.hatch_data }}</td>
              <td>{{ item.weight_low }} ~ {{ item.weight_high }}</td>
              <td>{{ item.height_low }} ~ {{ item.height_high }}</td>
              <td>
                <div class="ops-action-group">
                  <button type="button" class="ops-btn ops-btn-text" @click="editItem(item)">修改</button>
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

    <div v-if="drawerVisible" class="ops-modal-mask" @click="closeDrawer">
      <section class="ops-modal" @click.stop>
        <div class="ops-modal-header">
          <h3>{{ editingId ? '编辑孵化宠物' : '新增孵化宠物' }}</h3>
          <button type="button" class="ops-modal-close" @click="closeDrawer">✕</button>
        </div>

        <form class="ops-modal-body" @submit.prevent="submitForm">
          <div class="ops-form-grid">
            <div class="ops-form-item" style="grid-column:1/-1;">
              <label>关联宠物</label>
              <div style="display:grid;gap:10px;">
                <div v-if="selectedPokemon" style="display:flex;align-items:center;gap:12px;padding:10px 12px;border:1px solid var(--ops-border);border-radius:var(--ops-radius-sm);background:var(--ops-bg);">
                  <img v-if="selectedPokemon.image" :src="selectedPokemon.image" style="width:36px;height:36px;object-fit:contain;" alt="" />
                  <div style="display:grid;line-height:1.2;">
                    <strong>{{ selectedPokemon.name }}</strong>
                    <small style="color:var(--ops-muted);margin-top:4px;">编号 {{ selectedPokemon.no || '-' }}</small>
                  </div>
                  <span v-if="editingId" style="font-size:12px;color:var(--ops-muted);">（编辑时不可更换宠物）</span>
                </div>
                <div v-else style="color:var(--ops-muted);">尚未选择宠物</div>

                <div v-if="!editingId" style="display:grid;gap:8px;">
                  <input v-model="availableSearch" class="ops-input" type="text" placeholder="搜索未配置孵化数据的宠物" />
                  <div style="max-height:240px;overflow:auto;border:1px solid var(--ops-border);border-radius:var(--ops-radius-sm);background:var(--ops-surface);padding:6px;display:grid;gap:4px;">
                    <div v-if="availableLoading" style="color:var(--ops-muted);padding:8px;text-align:center;">加载中...</div>
                    <div v-else-if="!availablePokemon.length" style="color:var(--ops-muted);padding:8px;text-align:center;">暂无可选宠物</div>
                    <button
                      v-for="pokemon in availablePokemon"
                      :key="pokemon.id"
                      type="button"
                      :style="{
                        display:'grid',gridTemplateColumns:'24px 1fr auto',alignItems:'center',gap:'10px',
                        padding:'6px 10px',border:'1px solid transparent',borderRadius:'4px',cursor:'pointer',
                        textAlign:'left',fontSize:'13px',color:'var(--ops-text)',
                        background: selectedPokemon?.id === pokemon.id ? 'var(--ops-accent-light)' : 'transparent',
                        borderColor: selectedPokemon?.id === pokemon.id ? 'var(--ops-accent)' : 'transparent',
                      }"
                      @click="pickAvailablePokemon(pokemon)"
                    >
                      <img v-if="pokemon.image" :src="pokemon.image" style="width:24px;height:24px;object-fit:contain;" alt="" />
                      <span>{{ pokemon.name }}</span>
                      <span style="color:var(--ops-muted);font-size:12px;">编号 {{ pokemon.no || '-' }}</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div class="ops-form-item" style="grid-column:1/-1;">
              <label style="display:flex;align-items:center;gap:8px;">
                <input v-model="form.is_leader_form" type="checkbox" style="width:16px;height:16px;" />
                <span style="color:var(--ops-text-secondary);font-size:12px;">勾选表示该宠物为首领形态</span>
              </label>
            </div>

            <div class="ops-form-item" style="grid-column:1/-1;">
              <label>孵化时间(秒)</label>
              <input v-model.number="form.hatch_data" class="ops-input" type="number" min="0" />
            </div>

            <div class="ops-form-item">
              <label>体重下限(g)</label>
              <input v-model.number="form.weight_low" class="ops-input" type="number" min="0" />
            </div>
            <div class="ops-form-item">
              <label>体重上限(g)</label>
              <input v-model.number="form.weight_high" class="ops-input" type="number" min="0" />
            </div>

            <div class="ops-form-item">
              <label>身高下限(cm)</label>
              <input v-model.number="form.height_low" class="ops-input" type="number" min="0" />
            </div>
            <div class="ops-form-item">
              <label>身高上限(cm)</label>
              <input v-model.number="form.height_high" class="ops-input" type="number" min="0" />
            </div>
          </div>
          <div class="ops-modal-footer">
            <button type="submit" class="ops-btn ops-btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
            <button type="button" class="ops-btn ops-btn-secondary" @click="closeDrawer">取消</button>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>
