<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import {
  clearOpsToken,
  createOpsPetPrompt,
  deleteOpsPetPrompt,
  fetchOpsMe,
  fetchOpsPetPrompts,
  searchPokemonLineupPokemon,
  showOpsToast,
  updateOpsPetPrompt,
  type OpsPetPromptItem,
  type OpsPokemonLineupSearchItem,
} from '@/api/ops'

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const keyword = ref('')
const items = ref<OpsPetPromptItem[]>([])
const editingId = ref<number | null>(null)
const drawerVisible = ref(false)
const currentPage = ref(1)
const pageSize = 10
const total = ref(0)
const isAdmin = ref(false)

// 编辑器：编辑 / 预览 双标签
const editorTab = ref<'edit' | 'preview'>('edit')

// 宠物选择器
const petKeyword = ref('')
const petResults = ref<OpsPokemonLineupSearchItem[]>([])
const petDropdownVisible = ref(false)
let petSearchTimer: ReturnType<typeof setTimeout> | null = null

const form = reactive({
  pet_id: null as number | null,
  pet_name: '',
  pet_image: '',
  prompt: '',
  enabled: false,
})

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

// ── 极简 Markdown 渲染（无第三方依赖，仅用于预览） ──────────
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function renderInline(text: string): string {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
}

function renderMarkdown(src: string): string {
  const lines = (src || '').split('\n')
  const html: string[] = []
  let inCode = false
  let listType: 'ul' | 'ol' | null = null

  const closeList = () => {
    if (listType) {
      html.push(`</${listType}>`)
      listType = null
    }
  }

  for (const raw of lines) {
    const line = raw.replace(/\s+$/, '')

    if (line.trim().startsWith('```')) {
      if (inCode) {
        html.push('</code></pre>')
        inCode = false
      } else {
        closeList()
        html.push('<pre><code>')
        inCode = true
      }
      continue
    }
    if (inCode) {
      html.push(escapeHtml(raw))
      continue
    }

    const heading = /^(#{1,6})\s+(.*)$/.exec(line)
    if (heading) {
      closeList()
      const level = heading[1]!.length
      html.push(`<h${level}>${renderInline(heading[2]!)}</h${level}>`)
      continue
    }

    const ulItem = /^[-*]\s+(.*)$/.exec(line)
    if (ulItem) {
      if (listType !== 'ul') {
        closeList()
        html.push('<ul>')
        listType = 'ul'
      }
      html.push(`<li>${renderInline(ulItem[1]!)}</li>`)
      continue
    }

    const olItem = /^\d+\.\s+(.*)$/.exec(line)
    if (olItem) {
      if (listType !== 'ol') {
        closeList()
        html.push('<ol>')
        listType = 'ol'
      }
      html.push(`<li>${renderInline(olItem[1]!)}</li>`)
      continue
    }

    const quote = /^>\s?(.*)$/.exec(line)
    if (quote) {
      closeList()
      html.push(`<blockquote>${renderInline(quote[1]!)}</blockquote>`)
      continue
    }

    if (!line.trim()) {
      closeList()
      continue
    }

    closeList()
    html.push(`<p>${renderInline(line)}</p>`)
  }

  if (inCode) html.push('</code></pre>')
  closeList()
  return html.join('\n')
}

const previewHtml = computed(() => renderMarkdown(form.prompt))

async function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  await loadData()
}

function resetForm() {
  editingId.value = null
  form.pet_id = null
  form.pet_name = ''
  form.pet_image = ''
  form.prompt = ''
  form.enabled = false
  petKeyword.value = ''
  petResults.value = []
  petDropdownVisible.value = false
  editorTab.value = 'edit'
}

function openCreateDrawer() {
  resetForm()
  drawerVisible.value = true
}

function closeDrawer() {
  drawerVisible.value = false
  petDropdownVisible.value = false
}

function editItem(item: OpsPetPromptItem) {
  resetForm()
  editingId.value = item.id
  form.pet_id = item.pet_id
  form.pet_name = item.pet_name
  form.pet_image = item.pet_image
  form.prompt = item.prompt
  form.enabled = item.enabled
  drawerVisible.value = true
}

function onPetKeywordInput() {
  if (petSearchTimer) clearTimeout(petSearchTimer)
  const kw = petKeyword.value.trim()
  if (!kw) {
    petResults.value = []
    petDropdownVisible.value = false
    return
  }
  petSearchTimer = setTimeout(async () => {
    try {
      const res = await searchPokemonLineupPokemon(kw)
      petResults.value = res.items
      petDropdownVisible.value = true
    } catch {
      /* ignore */
    }
  }, 300)
}

function selectPet(pet: OpsPokemonLineupSearchItem) {
  form.pet_id = pet.id
  form.pet_name = pet.name
  form.pet_image = pet.image || ''
  petKeyword.value = ''
  petResults.value = []
  petDropdownVisible.value = false
}

function clearPet() {
  form.pet_id = null
  form.pet_name = ''
  form.pet_image = ''
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [me, data] = await Promise.all([
      fetchOpsMe(),
      fetchOpsPetPrompts({
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
    if (err?.response?.status === 401) {
      clearOpsToken()
      return
    }
    error.value = err?.response?.data?.detail || '加载失败'
  } finally {
    loading.value = false
  }
}

async function search() {
  currentPage.value = 1
  await loadData()
}

async function submitForm() {
  if (saving.value) return
  if (!form.pet_id) {
    showOpsToast('请选择宠物', 'error')
    return
  }
  if (!form.prompt.trim()) {
    showOpsToast('请填写 prompt', 'error')
    return
  }
  saving.value = true
  error.value = ''
  try {
    const payload = {
      pet_id: form.pet_id,
      prompt: form.prompt,
      enabled: form.enabled,
    }
    if (editingId.value) {
      await updateOpsPetPrompt(editingId.value, payload)
      showOpsToast('宠物 prompt 已更新', 'success')
    } else {
      await createOpsPetPrompt(payload)
      showOpsToast('宠物 prompt 已创建', 'success')
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

async function removeItem(item: OpsPetPromptItem) {
  if (!isAdmin.value) return
  if (!window.confirm(`确定删除宠物「${item.pet_name || item.pet_id}」的 prompt 吗？`)) return
  try {
    await deleteOpsPetPrompt(item.id)
    if (editingId.value === item.id) resetForm()
    await loadData()
    showOpsToast('宠物 prompt 已删除', 'success')
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '删除失败'
    showOpsToast(error.value, 'error')
  }
}

onMounted(() => {
  void loadData()
})

onBeforeUnmount(() => {
  if (petSearchTimer) clearTimeout(petSearchTimer)
})
</script>

<template>
  <div class="ops-page">
    <section class="ops-card-padded">
      <div class="ops-toolbar">
        <button type="button" class="ops-btn ops-btn-primary" @click="openCreateDrawer">新增</button>
        <input
          v-model="keyword"
          class="ops-input"
          type="text"
          placeholder="按宠物名称搜索"
          style="max-width:220px;"
          @keyup.enter="search"
        />
        <button type="button" class="ops-btn ops-btn-secondary" @click="search">搜索</button>
        <span class="ops-toolbar-meta">共 {{ total }} 条</span>
      </div>

      <p v-if="error" class="ops-error">{{ error }}</p>

      <div v-if="loading" class="ops-loading">加载中...</div>
      <div v-else-if="!items.length" class="ops-empty">
        <strong>暂无数据</strong>
        <span>点击「新增」为宠物配置对话 prompt。</span>
      </div>
      <div v-else class="ops-table-wrap">
        <table class="ops-table">
          <thead>
            <tr>
              <th class="ops-col-index">序号</th>
              <th>宠物</th>
              <th>Prompt 预览</th>
              <th>状态</th>
              <th class="ops-col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td>
                <div style="display:flex;align-items:center;gap:8px;">
                  <img
                    v-if="item.pet_image"
                    :src="item.pet_image"
                    style="width:40px;height:40px;border-radius:6px;object-fit:cover;"
                  />
                  <span>{{ item.pet_name || `#${item.pet_id}` }}</span>
                </div>
              </td>
              <td style="max-width:420px;color:var(--ops-muted);">
                <span style="display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                  {{ item.prompt || '-' }}
                </span>
              </td>
              <td>
                <span class="ops-badge" :class="item.enabled ? 'ops-badge--success' : 'ops-badge--default'">
                  {{ item.enabled ? '可用' : '禁用' }}
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

    <div v-if="drawerVisible" class="ops-modal-mask">
      <section class="ops-modal ops-modal-wide" @click.stop>
        <div class="ops-modal-header">
          <h3>{{ editingId ? '编辑宠物 Prompt' : '新增宠物 Prompt' }}</h3>
          <button type="button" class="ops-modal-close" @click="closeDrawer">✕</button>
        </div>

        <form class="ops-modal-body" @submit.prevent="submitForm">
          <div class="ops-form-grid">
            <div class="ops-form-row" style="position:relative;">
              <span>宠物</span>
              <div v-if="form.pet_id" style="display:flex;align-items:center;gap:8px;">
                <img v-if="form.pet_image" :src="form.pet_image" style="width:36px;height:36px;border-radius:6px;object-fit:cover;" />
                <span>{{ form.pet_name || `#${form.pet_id}` }}</span>
                <button type="button" class="ops-btn ops-btn-text ops-btn--danger" @click="clearPet">重选</button>
              </div>
              <template v-else>
                <input
                  v-model="petKeyword"
                  class="ops-input"
                  type="text"
                  placeholder="输入宠物名称搜索"
                  @input="onPetKeywordInput"
                />
                <ul
                  v-if="petDropdownVisible && petResults.length"
                  style="position:absolute;top:100%;left:0;right:0;z-index:20;margin:4px 0 0;padding:4px;list-style:none;max-height:220px;overflow:auto;background:#fff;border:1px solid var(--ops-border);border-radius:6px;box-shadow:0 6px 18px rgba(0,0,0,.12);"
                >
                  <li
                    v-for="pet in petResults"
                    :key="pet.id"
                    style="display:flex;align-items:center;gap:8px;padding:6px 8px;cursor:pointer;border-radius:4px;"
                    @click="selectPet(pet)"
                  >
                    <img v-if="pet.image" :src="pet.image" style="width:32px;height:32px;border-radius:5px;object-fit:cover;" />
                    <span>{{ pet.name }}</span>
                  </li>
                </ul>
              </template>
            </div>

            <label class="ops-form-row">
              <span>是否可用</span>
              <select v-model="form.enabled" class="ops-select">
                <option :value="true">可用</option>
                <option :value="false">禁用</option>
              </select>
            </label>
          </div>

          <div style="margin-top:18px;">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
              <span style="font-size:13px;font-weight:600;color:var(--ops-text);">人设 Prompt（支持 Markdown）</span>
              <div class="ops-tab-group" style="display:flex;gap:4px;">
                <button
                  type="button"
                  class="ops-btn ops-btn-sm"
                  :class="editorTab === 'edit' ? 'ops-btn-primary' : 'ops-btn-secondary'"
                  @click="editorTab = 'edit'"
                >编辑</button>
                <button
                  type="button"
                  class="ops-btn ops-btn-sm"
                  :class="editorTab === 'preview' ? 'ops-btn-primary' : 'ops-btn-secondary'"
                  @click="editorTab = 'preview'"
                >预览</button>
              </div>
            </div>

            <textarea
              v-show="editorTab === 'edit'"
              v-model="form.prompt"
              class="ops-input"
              rows="24"
              placeholder="在此编写宠物人设，支持 Markdown 语法（# 标题、**加粗**、- 列表、`代码` 等）"
              style="width:100%;min-height:480px;resize:vertical;font-family:'Consolas','Menlo',monospace;line-height:1.6;"
            ></textarea>

            <div
              v-show="editorTab === 'preview'"
              class="md-preview"
              style="min-height:480px;padding:14px;border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);overflow:auto;"
              v-html="previewHtml"
            ></div>
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

<style scoped>
.md-preview :deep(h1),
.md-preview :deep(h2),
.md-preview :deep(h3),
.md-preview :deep(h4) {
  margin: 0.6em 0 0.4em;
  font-weight: 600;
  line-height: 1.3;
}
.md-preview :deep(h1) { font-size: 1.5em; }
.md-preview :deep(h2) { font-size: 1.3em; }
.md-preview :deep(h3) { font-size: 1.15em; }
.md-preview :deep(p) { margin: 0.5em 0; line-height: 1.7; }
.md-preview :deep(ul),
.md-preview :deep(ol) { margin: 0.5em 0; padding-left: 1.6em; }
.md-preview :deep(li) { margin: 0.2em 0; line-height: 1.6; }
.md-preview :deep(blockquote) {
  margin: 0.6em 0;
  padding: 0.2em 0.9em;
  border-left: 3px solid var(--ops-border);
  color: var(--ops-muted);
}
.md-preview :deep(code) {
  padding: 0.1em 0.35em;
  background: rgba(127, 127, 127, 0.14);
  border-radius: 4px;
  font-family: 'Consolas', 'Menlo', monospace;
  font-size: 0.92em;
}
.md-preview :deep(pre) {
  margin: 0.6em 0;
  padding: 0.8em 1em;
  background: rgba(127, 127, 127, 0.1);
  border-radius: 6px;
  overflow: auto;
}
.md-preview :deep(pre code) {
  padding: 0;
  background: none;
}
.md-preview :deep(a) { color: #2563eb; text-decoration: underline; }
</style>
