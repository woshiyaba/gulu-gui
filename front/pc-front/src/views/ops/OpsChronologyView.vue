<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  clearOpsToken,
  createOpsChronology,
  deleteOpsChronology,
  fetchOpsChronology,
  fetchOpsMe,
  showOpsToast,
  updateOpsChronology,
  uploadOpsChronologyImage,
  type OpsChronologyItem,
} from '@/api/ops'

const loading = ref(false)
const saving = ref(false)
const uploadingImage = ref(false)
const error = ref('')
const keyword = ref('')
const items = ref<OpsChronologyItem[]>([])
const editingId = ref<number | null>(null)
const drawerVisible = ref(false)
const currentPage = ref(1)
const pageSize = 10
const total = ref(0)
const isAdmin = ref(false)

const imageInputRef = ref<HTMLInputElement | null>(null)

const form = reactive({
  event_date: '',
  title: '',
  content: '',
  images: [] as string[],
  sort_order: 0,
  is_active: true,
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

async function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  await loadData()
}

function resetForm() {
  editingId.value = null
  form.event_date = ''
  form.title = ''
  form.content = ''
  form.images = []
  form.sort_order = 0
  form.is_active = true
  if (imageInputRef.value) imageInputRef.value.value = ''
}

function openCreateDrawer() {
  resetForm()
  drawerVisible.value = true
}

function closeDrawer() {
  drawerVisible.value = false
}

function editItem(item: OpsChronologyItem) {
  editingId.value = item.id
  form.event_date = item.event_date
  form.title = item.title
  form.content = item.content
  form.images = [...item.images]
  form.sort_order = item.sort_order
  form.is_active = item.is_active
  drawerVisible.value = true
}

async function onImagesSelected(ev: Event) {
  const input = ev.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (!files.length) return
  uploadingImage.value = true
  try {
    for (const file of files) {
      const data = await uploadOpsChronologyImage(file)
      form.images.push(data.url)
    }
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '图片上传失败', 'error')
  } finally {
    uploadingImage.value = false
    if (imageInputRef.value) imageInputRef.value.value = ''
  }
}

function removeImage(idx: number) {
  form.images.splice(idx, 1)
}

function moveImage(idx: number, dir: -1 | 1) {
  const target = idx + dir
  if (target < 0 || target >= form.images.length) return
  const [moved] = form.images.splice(idx, 1)
  if (moved !== undefined) form.images.splice(target, 0, moved)
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [me, data] = await Promise.all([
      fetchOpsMe(),
      fetchOpsChronology({
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
  if (!form.event_date) {
    showOpsToast('请选择时间', 'error')
    return
  }
  saving.value = true
  error.value = ''
  try {
    const payload = {
      event_date: form.event_date,
      title: form.title.trim(),
      content: form.content,
      images: form.images.filter((url) => url.trim()),
      sort_order: Number(form.sort_order) || 0,
      is_active: form.is_active,
    }
    if (editingId.value) {
      await updateOpsChronology(editingId.value, payload)
      showOpsToast('大事记已更新', 'success')
    } else {
      await createOpsChronology(payload)
      showOpsToast('大事记已创建', 'success')
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

async function removeItem(item: OpsChronologyItem) {
  if (!isAdmin.value) return
  if (!window.confirm(`确定删除大事记「${item.title || item.event_date}」吗？`)) return
  try {
    await deleteOpsChronology(item.id)
    if (editingId.value === item.id) resetForm()
    await loadData()
    showOpsToast('大事记已删除', 'success')
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '删除失败'
    showOpsToast(error.value, 'error')
  }
}

onMounted(() => {
  void loadData()
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
          placeholder="按标题搜索"
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
        <span>点击「新增」添加一条大事记。</span>
      </div>
      <div v-else class="ops-table-wrap">
        <table class="ops-table">
          <thead>
            <tr>
              <th class="ops-col-index">序号</th>
              <th>时间</th>
              <th>标题</th>
              <th>封面</th>
              <th>图片数</th>
              <th class="ops-col-sort">排序</th>
              <th>状态</th>
              <th class="ops-col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ pageStart + index }}</td>
              <td>{{ item.event_date }}</td>
              <td>{{ item.title || '-' }}</td>
              <td>
                <img v-if="item.images.length" :src="item.images[0]" style="max-width:120px;max-height:48px;border-radius:4px;object-fit:cover;" />
                <span v-else style="color:var(--ops-muted);">无</span>
              </td>
              <td>{{ item.images.length }}</td>
              <td>{{ item.sort_order }}</td>
              <td>
                <span class="ops-badge" :class="item.is_active ? 'ops-badge--success' : 'ops-badge--default'">
                  {{ item.is_active ? '展示中' : '已隐藏' }}
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
          <h3>{{ editingId ? '编辑大事记' : '新增大事记' }}</h3>
          <button type="button" class="ops-modal-close" @click="closeDrawer">✕</button>
        </div>

        <form class="ops-modal-body" @submit.prevent="submitForm">
          <div class="ops-form-grid">
            <label class="ops-form-row">
              <span>时间</span>
              <input v-model="form.event_date" class="ops-input" required type="date" />
            </label>
            <label class="ops-form-row">
              <span>标题</span>
              <input v-model="form.title" class="ops-input" type="text" placeholder="事件标题" />
            </label>
            <label class="ops-form-row">
              <span>排序</span>
              <input v-model="form.sort_order" class="ops-input" type="number" placeholder="同日越大越靠前" />
            </label>
            <label class="ops-form-row">
              <span>是否展示</span>
              <select v-model="form.is_active" class="ops-select">
                <option :value="true">展示</option>
                <option :value="false">隐藏</option>
              </select>
            </label>
          </div>

          <label class="ops-form-row" style="margin-top:14px;display:block;">
            <span style="display:block;margin-bottom:6px;">正文</span>
            <textarea v-model="form.content" class="ops-input" rows="6" placeholder="事件正文内容" style="width:100%;resize:vertical;"></textarea>
          </label>

          <div style="margin-top:18px;border:1px solid var(--ops-border);border-radius:var(--ops-radius-md);padding:14px;">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
              <span style="font-size:13px;font-weight:600;color:var(--ops-text);">图片（可多张，第一张作封面）</span>
              <span style="font-size:12px;color:var(--ops-muted);">已添加 {{ form.images.length }} 张</span>
            </div>

            <input
              ref="imageInputRef"
              type="file"
              accept="image/*"
              multiple
              style="display:none"
              @change="onImagesSelected"
            />
            <button type="button" class="ops-btn ops-btn-secondary ops-btn-sm" :disabled="uploadingImage" @click="imageInputRef?.click()">
              {{ uploadingImage ? '上传中...' : '添加图片' }}
            </button>

            <div v-if="form.images.length" style="margin-top:12px;display:flex;flex-wrap:wrap;gap:10px;">
              <div
                v-for="(url, idx) in form.images"
                :key="idx"
                style="position:relative;width:96px;border:1px solid var(--ops-border);border-radius:6px;overflow:hidden;"
              >
                <img :src="url" style="width:96px;height:96px;object-fit:cover;display:block;" />
                <div style="display:flex;justify-content:space-between;padding:2px 4px;background:var(--ops-bg, #f5f7fb);">
                  <button type="button" class="ops-btn ops-btn-text" :disabled="idx === 0" style="padding:0 4px;" @click="moveImage(idx, -1)">←</button>
                  <button type="button" class="ops-btn ops-btn-text ops-btn--danger" style="padding:0 4px;" @click="removeImage(idx)">删</button>
                  <button type="button" class="ops-btn ops-btn-text" :disabled="idx === form.images.length - 1" style="padding:0 4px;" @click="moveImage(idx, 1)">→</button>
                </div>
              </div>
            </div>
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
