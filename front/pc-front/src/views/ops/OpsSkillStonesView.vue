<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  clearOpsToken,
  createOpsSkillStone,
  deleteOpsSkillStone,
  fetchOpsMe,
  fetchOpsSkillOptions,
  fetchOpsSkillStoneAvailableSkills,
  fetchOpsSkillStoneDetail,
  fetchOpsSkillStones,
  showOpsToast,
  updateOpsSkillStone,
  type OpsSkillStoneAvailableSkill,
  type OpsSkillStoneItem,
} from '@/api/ops'

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const keyword = ref('')
const attr = ref('')
const type = ref('')
const obtainKeyword = ref('')
const items = ref<OpsSkillStoneItem[]>([])
const editingId = ref<number | null>(null)
const drawerVisible = ref(false)
const currentPage = ref(1)
const pageSize = 10
const total = ref(0)

const attrOptions = ref<string[]>([])
const typeOptions = ref<string[]>([])

const form = reactive({
  skill_id: 0 as number,
  obtain_method: '',
})

const selectedSkill = ref<OpsSkillStoneAvailableSkill | null>(null)
const availableSearch = ref('')
const availableLoading = ref(false)
const availableSkills = ref<OpsSkillStoneAvailableSkill[]>([])
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
  form.skill_id = 0
  form.obtain_method = ''
  selectedSkill.value = null
  availableSearch.value = ''
  availableSkills.value = []
}

function openCreateDrawer() {
  resetForm()
  drawerVisible.value = true
  void loadAvailableSkills()
}

function closeDrawer() {
  drawerVisible.value = false
}

async function editItem(item: OpsSkillStoneItem) {
  try {
    const detail = await fetchOpsSkillStoneDetail(item.id)
    editingId.value = detail.id
    form.skill_id = detail.skill_id
    form.obtain_method = detail.obtain_method
    selectedSkill.value = {
      id: detail.skill_id,
      name: detail.skill_name,
      attr: detail.skill_attr,
      type: detail.skill_type,
      icon: detail.skill_icon,
      icon_url: detail.skill_icon_url,
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
    const [me, resp, options] = await Promise.all([
      fetchOpsMe(),
      fetchOpsSkillStones({
        keyword: keyword.value.trim() || undefined,
        attr: attr.value.trim() || undefined,
        type: type.value.trim() || undefined,
        obtain_keyword: obtainKeyword.value.trim() || undefined,
        page: currentPage.value,
        page_size: pageSize,
      }),
      fetchOpsSkillOptions(),
    ])
    void me
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
  obtainKeyword.value = ''
  currentPage.value = 1
  await loadData()
}

async function loadAvailableSkills() {
  availableLoading.value = true
  try {
    const resp = await fetchOpsSkillStoneAvailableSkills({
      keyword: availableSearch.value.trim() || undefined,
      limit: 30,
    })
    availableSkills.value = resp.items
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '加载技能失败', 'error')
  } finally {
    availableLoading.value = false
  }
}

watch(availableSearch, () => {
  if (editingId.value) return
  if (availableTimer) window.clearTimeout(availableTimer)
  availableTimer = window.setTimeout(() => {
    void loadAvailableSkills()
  }, 250)
})

function pickAvailableSkill(skill: OpsSkillStoneAvailableSkill) {
  selectedSkill.value = skill
  form.skill_id = skill.id
}

async function submitForm() {
  if (saving.value) return
  saving.value = true
  error.value = ''
  try {
    if (!editingId.value && !form.skill_id) {
      showOpsToast('请选择技能', 'error')
      return
    }
    if (!form.obtain_method.trim()) {
      showOpsToast('获取方式不能为空', 'error')
      return
    }
    if (editingId.value) {
      await updateOpsSkillStone(editingId.value, { obtain_method: form.obtain_method.trim() })
      showOpsToast('技能石已更新', 'success')
    } else {
      await createOpsSkillStone({
        skill_id: form.skill_id,
        obtain_method: form.obtain_method.trim(),
      })
      showOpsToast('技能石已创建', 'success')
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

async function removeItem(item: OpsSkillStoneItem) {
  if (!window.confirm(`确定删除「${item.skill_name}」的技能石获取方式吗？`)) return
  try {
    await deleteOpsSkillStone(item.id)
    if (editingId.value === item.id) resetForm()
    await loadData()
    showOpsToast('技能石已删除', 'success')
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
        <label class="ops-form-item" style="min-width:200px;">
          <span class="ops-filter-label">获取方式</span>
          <input v-model="obtainKeyword" class="ops-input" type="text" placeholder="包含的关键词" />
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
        <span>请调整筛选条件后重试，或新增技能石。</span>
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
              <th style="max-width:320px;">获取方式</th>
              <th style="width:160px;">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td>
                <img v-if="item.skill_icon_url" :src="item.skill_icon_url" style="width:36px;height:36px;object-fit:contain;vertical-align:middle;" alt="" />
                <span v-else style="color:var(--ops-muted);">-</span>
              </td>
              <td>{{ item.skill_name }}</td>
              <td>{{ item.skill_attr || '-' }}</td>
              <td>{{ item.skill_type || '-' }}</td>
              <td style="max-width:320px;text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" :title="item.obtain_method">{{ item.obtain_method || '-' }}</td>
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
          <h3>{{ editingId ? '编辑技能石' : '新增技能石' }}</h3>
          <button type="button" class="ops-modal-close" @click="closeDrawer">✕</button>
        </div>

        <form class="ops-modal-body" @submit.prevent="submitForm">
          <div class="ops-form-grid" style="grid-template-columns:1fr;">
            <div class="ops-form-row ops-form-grid-full" style="align-items:flex-start;">
              <span>关联技能</span>
              <div style="display:grid;gap:10px;">
                <div v-if="selectedSkill" style="display:flex;align-items:center;gap:12px;padding:10px 12px;border:1px solid var(--ops-border);border-radius:var(--ops-radius-sm);background:var(--ops-bg);">
                  <img v-if="selectedSkill.icon_url" :src="selectedSkill.icon_url" style="width:36px;height:36px;object-fit:contain;" alt="" />
                  <div style="display:grid;line-height:1.2;">
                    <strong>{{ selectedSkill.name }}</strong>
                    <small style="color:var(--ops-muted);margin-top:4px;">{{ selectedSkill.attr || '-' }} · {{ selectedSkill.type || '-' }}</small>
                  </div>
                  <span v-if="editingId" style="font-size:12px;color:var(--ops-muted);">（编辑时不可更换技能）</span>
                </div>
                <div v-else style="color:var(--ops-muted);">尚未选择技能</div>

                <div v-if="!editingId" style="display:grid;gap:8px;">
                  <input v-model="availableSearch" class="ops-input" type="text" placeholder="搜索未挂技能石的技能" />
                  <div style="max-height:240px;overflow:auto;border:1px solid var(--ops-border);border-radius:var(--ops-radius-sm);background:var(--ops-surface);padding:6px;display:grid;gap:4px;">
                    <div v-if="availableLoading" style="color:var(--ops-muted);padding:8px;text-align:center;">加载中...</div>
                    <div v-else-if="!availableSkills.length" style="color:var(--ops-muted);padding:8px;text-align:center;">暂无可选技能</div>
                    <button
                      v-for="skill in availableSkills"
                      :key="skill.id"
                      type="button"
                      :style="{
                        display:'grid',gridTemplateColumns:'24px 1fr auto',alignItems:'center',gap:'10px',
                        padding:'6px 10px',border:'1px solid transparent',borderRadius:'4px',cursor:'pointer',
                        textAlign:'left',fontSize:'13px',color:'var(--ops-text)',
                        background: selectedSkill?.id === skill.id ? 'var(--ops-accent-light)' : 'transparent',
                        borderColor: selectedSkill?.id === skill.id ? 'var(--ops-accent)' : 'transparent',
                      }"
                      @click="pickAvailableSkill(skill)"
                    >
                      <img v-if="skill.icon_url" :src="skill.icon_url" style="width:24px;height:24px;object-fit:contain;" alt="" />
                      <span>{{ skill.name }}</span>
                      <span style="color:var(--ops-muted);font-size:12px;">{{ skill.attr || '-' }} · {{ skill.type || '-' }}</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <label class="ops-form-row ops-form-grid-full" style="align-items:flex-start;">
              <span>获取方式</span>
              <textarea
                v-model="form.obtain_method"
                class="ops-input"
                style="height:auto;min-height:72px;padding:8px 12px;resize:vertical;"
                rows="3"
                maxlength="255"
                placeholder="例如：XX 使用 YY 指定次数(可在游戏图鉴中查看具体次数)"
              />
            </label>
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
