<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  clearOpsToken,
  fetchOpsAnnouncement,
  showOpsToast,
  updateOpsAnnouncement,
} from '@/api/ops'

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const updatedAt = ref<string | null>(null)

const form = reactive({
  title: '',
  content: '',
  is_active: false,
})

function formatTime(value: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchOpsAnnouncement()
    form.title = data.title
    form.content = data.content
    form.is_active = data.is_active
    updatedAt.value = data.updated_at
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

async function submitForm() {
  if (saving.value) return
  saving.value = true
  error.value = ''
  try {
    const data = await updateOpsAnnouncement({
      title: form.title.trim(),
      content: form.content,
      is_active: form.is_active,
    })
    form.title = data.title
    form.content = data.content
    form.is_active = data.is_active
    updatedAt.value = data.updated_at
    showOpsToast('公告已保存', 'success')
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '保存失败'
    showOpsToast(error.value, 'error')
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="ops-page">
    <section class="ops-card-padded">
      <div class="ops-toolbar">
        <span class="ops-toolbar-meta">前台首页弹窗公告，启用后用户进入首页时展示。</span>
        <span class="ops-toolbar-meta">最近更新：{{ formatTime(updatedAt) }}</span>
      </div>

      <p v-if="error" class="ops-error">{{ error }}</p>
      <div v-if="loading" class="ops-loading">加载中...</div>

      <form v-else class="announce-form" @submit.prevent="submitForm">
        <label class="announce-field">
          <span class="announce-label">状态</span>
          <span class="announce-switch">
            <label class="announce-radio">
              <input v-model="form.is_active" type="radio" :value="true" />
              启用
            </label>
            <label class="announce-radio">
              <input v-model="form.is_active" type="radio" :value="false" />
              禁用
            </label>
            <span class="ops-badge" :class="form.is_active ? 'ops-badge--success' : 'ops-badge--default'">
              {{ form.is_active ? '前台将展示公告' : '前台不展示公告' }}
            </span>
          </span>
        </label>

        <label class="announce-field">
          <span class="announce-label">标题</span>
          <input v-model="form.title" class="ops-input" type="text" maxlength="200" placeholder="公告标题（可留空）" />
        </label>

        <label class="announce-field">
          <span class="announce-label">正文</span>
          <textarea
            v-model="form.content"
            class="ops-input announce-textarea"
            rows="8"
            placeholder="公告正文，支持多行换行"
          ></textarea>
        </label>

        <div class="announce-actions">
          <button type="submit" class="ops-btn ops-btn-primary" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </form>

      <!-- 前台展示预览 -->
      <div v-if="!loading" class="announce-preview">
        <div class="announce-preview-title">前台弹窗预览</div>
        <div class="announce-preview-card" :class="{ disabled: !form.is_active }">
          <div class="announce-preview-head">
            <strong>📢 {{ form.title || '公告' }}</strong>
            <span class="announce-preview-x">✕</span>
          </div>
          <div class="announce-preview-body">{{ form.content || '（正文为空）' }}</div>
          <div class="announce-preview-foot">
            <span>☐ 今日不再提示</span>
            <span class="announce-preview-btn">我知道了</span>
          </div>
        </div>
        <p v-if="!form.is_active" class="announce-preview-hint">当前为禁用状态，前台不会弹出该公告。</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.announce-form {
  display: grid;
  gap: 18px;
  max-width: 640px;
}

.announce-field {
  display: grid;
  gap: 8px;
}

.announce-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ops-text);
}

.announce-switch {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.announce-radio {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--ops-text);
  cursor: pointer;
}

.announce-radio input {
  margin: 0;
  cursor: pointer;
}

.announce-textarea {
  height: auto;
  min-height: 160px;
  padding: 10px 12px;
  line-height: 1.6;
  resize: vertical;
  font-family: inherit;
}

.announce-actions {
  display: flex;
  gap: 12px;
}

.announce-preview {
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px dashed var(--ops-border);
}

.announce-preview-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--ops-text-secondary);
  margin-bottom: 12px;
}

.announce-preview-card {
  width: min(100%, 420px);
  border: 1px solid var(--ops-border);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.1);
}

.announce-preview-card.disabled {
  opacity: 0.55;
}

.announce-preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--ops-border);
  font-size: 14px;
  color: var(--ops-accent);
}

.announce-preview-x {
  color: var(--ops-muted);
}

.announce-preview-body {
  padding: 14px 16px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--ops-text);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
}

.announce-preview-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-top: 1px solid var(--ops-border);
  font-size: 12px;
  color: var(--ops-muted);
}

.announce-preview-btn {
  padding: 4px 14px;
  border-radius: 14px;
  background: var(--ops-accent);
  color: #fff;
}

.announce-preview-hint {
  margin-top: 10px;
  font-size: 12px;
  color: var(--ops-muted);
}
</style>
