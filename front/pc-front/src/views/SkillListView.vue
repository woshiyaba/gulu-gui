<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AttributeFilter from '@/components/AttributeFilter.vue'
import { fetchAttributes, fetchSkillTypes, fetchSkills } from '@/api/pokemon'
import { useTheme } from '@/composables/useTheme'
import type { Attribute, Skill } from '@/types'

const router = useRouter()
const { isDark, toggleTheme } = useTheme()

const keyword = ref('')
const selectedType = ref('')
const selectedAttr = ref('')
const loading = ref(false)
const error = ref('')
const skills = ref<Skill[]>([])
const total = ref(0)
const hasLoaded = ref(false)

const attributes = ref<Attribute[]>([])
const skillTypes = ref<string[]>([])

const summaryText = computed(() => {
  if (!hasLoaded.value) return ''
  const parts: string[] = []
  if (keyword.value.trim()) parts.push(`名称"${keyword.value.trim()}"`)
  if (selectedType.value) parts.push(`类型"${selectedType.value}"`)
  if (selectedAttr.value) parts.push(`属性"${selectedAttr.value}"`)
  const prefix = parts.length ? `筛选条件：${parts.join('、')}，` : ''
  return `${prefix}共匹配到 ${total.value} 个技能。`
})

async function loadSkills() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchSkills({
      name: keyword.value || undefined,
      skill_type: selectedType.value || undefined,
      attr: selectedAttr.value || undefined,
    })
    skills.value = res.items
    total.value = res.total
    hasLoaded.value = true
  } catch {
    error.value = '查询失败，请确认后端服务已启动'
    skills.value = []
    total.value = 0
    hasLoaded.value = true
  } finally {
    loading.value = false
  }
}

function onSearch() {
  void loadSkills()
}

function onReset() {
  keyword.value = ''
  selectedType.value = ''
  selectedAttr.value = ''
  void loadSkills()
}

function onAttrChange(attrs: string[]) {
  selectedAttr.value = attrs.length ? (attrs[attrs.length - 1] ?? '') : ''
}

watch([selectedType, selectedAttr], () => {
  void loadSkills()
})

onMounted(async () => {
  const [attrs, types] = await Promise.all([
    fetchAttributes().catch(() => []),
    fetchSkillTypes().catch(() => []),
  ])
  attributes.value = attrs
  skillTypes.value = types
  await loadSkills()
})
</script>

<template>
  <div class="skill-list-page">
    <header class="page-header">
      <button class="back-btn" @click="router.push('/')">← 返回图鉴</button>
      <h1 class="page-title">技能图鉴</h1>
      <button class="theme-btn" @click="toggleTheme">
        {{ isDark ? '切换浅色' : '夜间模式' }}
      </button>
    </header>

    <main class="page-main">
      <section class="card search-card">
        <h2 class="section-title">筛选技能</h2>

        <div class="search-row">
          <input
            v-model="keyword"
            class="search-input"
            type="text"
            placeholder="搜索技能名称..."
            @keyup.enter="onSearch"
          />

          <select v-model="selectedType" class="type-select">
            <option value="">全部类型</option>
            <option v-for="t in skillTypes" :key="t" :value="t">{{ t }}</option>
          </select>

          <button class="action-btn primary-btn" :disabled="loading" @click="onSearch">
            {{ loading ? '查询中...' : '开始查询' }}
          </button>
          <button class="action-btn secondary-btn" :disabled="loading" @click="onReset">
            重置
          </button>
        </div>

        <AttributeFilter
          :attributes="attributes"
          :selected="selectedAttr ? [selectedAttr] : []"
          @change="onAttrChange"
        />
      </section>

      <div v-if="error" class="error-msg">{{ error }}</div>

      <section v-if="hasLoaded" class="card result-card">
        <div class="result-head">
          <h2 class="section-title">查询结果</h2>
          <span class="result-summary">{{ summaryText }}</span>
        </div>

        <div v-if="loading" class="skeleton-grid">
          <div v-for="n in 12" :key="n" class="skeleton-card"></div>
        </div>

        <div v-else-if="skills.length === 0" class="empty-msg">
          没有找到匹配的技能
        </div>

        <div v-else class="skill-grid">
          <article v-for="item in skills" :key="item.name" class="skill-card">
            <div class="skill-icon-wrap">
              <img
                v-if="item.icon"
                :src="item.icon"
                :alt="item.name"
                class="skill-icon"
                loading="lazy"
              />
              <div v-else class="skill-icon-placeholder">?</div>
            </div>
            <div class="skill-body">
              <h3 class="skill-name">{{ item.name }}</h3>
              <div class="skill-tags">
                <span v-if="item.attr" class="tag tag-attr">{{ item.attr }}</span>
                <span v-if="item.type" class="tag tag-type">{{ item.type }}</span>
              </div>
              <div class="skill-stats">
                <span v-if="item.power" class="stat">威力 {{ item.power }}</span>
                <span v-if="item.consume" class="stat">消耗 {{ item.consume }}</span>
              </div>
              <p v-if="item.desc" class="skill-desc">{{ item.desc }}</p>
            </div>
          </article>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.skill-list-page {
  min-height: 100vh;
  background: var(--color-bg);
}

.page-header {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  padding: 14px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.page-title {
  flex: 1;
  margin: 0;
  font-size: 22px;
  color: var(--color-accent);
}

.back-btn,
.theme-btn,
.action-btn {
  border-radius: 20px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.back-btn {
  padding: 6px 16px;
  border: 2px solid var(--color-accent);
  background: transparent;
  color: var(--color-accent);
}

.theme-btn {
  padding: 8px 16px;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
}

.page-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
}

.section-title {
  margin: 0 0 12px;
  font-size: 20px;
  color: var(--color-text);
}

.search-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 8px;
}

.search-input {
  flex: 1;
  min-width: 0;
  padding: 10px 14px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 14px;
  outline: none;
}

.search-input:focus {
  border-color: var(--color-accent);
}

.type-select {
  height: 40px;
  padding: 0 12px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 14px;
  outline: none;
}

.type-select:focus {
  border-color: var(--color-accent);
}

.action-btn {
  padding: 10px 18px;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.primary-btn {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.secondary-btn {
  color: var(--color-muted);
}

.back-btn:hover,
.theme-btn:hover,
.action-btn:hover:not(:disabled) {
  background: var(--color-hover);
}

.error-msg {
  margin-bottom: 20px;
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  color: #f87171;
}

.result-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}

.result-summary {
  color: var(--color-muted);
  font-size: 14px;
  line-height: 1.7;
}

.skill-grid,
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.skill-card {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: var(--color-bg);
  transition: border-color 0.2s ease;
}

.skill-card:hover {
  border-color: var(--color-accent);
}

.skill-icon-wrap {
  width: 64px;
  height: 64px;
  border-radius: 12px;
  background: var(--color-img-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}

.skill-icon {
  width: 48px;
  height: 48px;
  object-fit: contain;
}

.skill-icon-placeholder {
  font-size: 24px;
  color: var(--color-muted);
}

.skill-body {
  min-width: 0;
  flex: 1;
}

.skill-name {
  margin: 0 0 6px;
  color: var(--color-text);
  font-size: 16px;
  font-weight: 700;
}

.skill-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.tag {
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.tag-attr {
  background: var(--color-tag-bg);
  color: var(--color-accent);
}

.tag-type {
  background: rgba(100, 116, 139, 0.12);
  color: var(--color-muted);
}

.skill-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 4px;
}

.stat {
  font-size: 13px;
  color: var(--color-muted);
}

.skill-desc {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--color-muted);
  line-height: 1.6;
  word-break: break-word;
}

.empty-msg {
  padding: 24px 0 8px;
  text-align: center;
  color: var(--color-muted);
}

.skeleton-card {
  height: 120px;
  border-radius: 14px;
  background: var(--color-bg);
  animation: shimmer 1.4s infinite;
}

@keyframes shimmer {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}

@media (max-width: 720px) {
  .page-header {
    flex-wrap: wrap;
  }

  .page-title {
    width: 100%;
  }

  .page-main {
    padding: 16px;
  }

  .search-row {
    flex-direction: column;
    align-items: stretch;
  }

  .result-head {
    flex-direction: column;
  }
}
</style>
