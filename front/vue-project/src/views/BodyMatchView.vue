<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchPokemonBodyMatch } from '@/api/pokemon'
import { useTheme } from '@/composables/useTheme'
import type { PokemonBodyMatchResponse } from '@/types'

const router = useRouter()
const { isDark, toggleTheme } = useTheme()

const heightInput = ref('')
const weightInput = ref('')
const loading = ref(false)
const error = ref('')
const result = ref<PokemonBodyMatchResponse | null>(null)

const hasSearched = computed(() => result.value !== null)

function parsePositiveNumber(raw: string): number | null {
  const value = Number(raw)
  if (!Number.isFinite(value) || value <= 0) {
    return null
  }
  return value
}

async function onSubmit() {
  const heightM = parsePositiveNumber(heightInput.value)
  const weightKg = parsePositiveNumber(weightInput.value)

  if (heightM === null || weightKg === null) {
    error.value = '请输入大于 0 的身高（m）和体重（kg）'
    result.value = null
    return
  }

  loading.value = true
  error.value = ''
  try {
    result.value = await fetchPokemonBodyMatch({
      height_m: heightM,
      weight_kg: weightKg,
    })
  } catch {
    error.value = '查询失败，请确认后端服务已启动且数据表已导入'
    result.value = null
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="body-match-page">
    <header class="page-header">
      <button class="back-btn" @click="router.push('/')">← 返回图鉴</button>
      <h1 class="page-title">量体查宠</h1>
      <button class="theme-btn" @click="toggleTheme">
        {{ isDark ? '切换浅色' : '夜间模式' }}
      </button>
    </header>

    <main class="page-main">
      <section class="card form-card">
        <h2 class="section-title">输入体型</h2>
        <p class="helper-text">输入身高（m）和体重（kg），系统会自动换算成 cm / g 后进行区间匹配。</p>

        <div class="form-grid">
          <label class="field">
            <span class="field-label">身高（m）</span>
            <input
              v-model="heightInput"
              class="field-input"
              type="number"
              min="0"
              step="0.01"
              placeholder="例如 0.27"
              @keyup.enter="onSubmit"
            />
          </label>

          <label class="field">
            <span class="field-label">体重（kg）</span>
            <input
              v-model="weightInput"
              class="field-input"
              type="number"
              min="0"
              step="0.001"
              placeholder="例如 1.36"
              @keyup.enter="onSubmit"
            />
          </label>
        </div>

        <div class="actions">
          <button class="submit-btn" :disabled="loading" @click="onSubmit">
            {{ loading ? '查询中...' : '开始查询' }}
          </button>
        </div>
      </section>

      <div v-if="error" class="error-msg">{{ error }}</div>

      <section v-if="result" class="card result-card">
        <h2 class="section-title">查询结果</h2>
        <div class="result-summary">
          输入 {{ result.height_m }} m / {{ result.weight_kg }} kg，
          已换算为 {{ result.height_cm }} cm / {{ result.weight_g }} g，
          共匹配到 {{ result.total }} 只宠物。
        </div>

        <div v-if="result.total === 0" class="empty-msg">
          没有找到符合这组身高和体重区间的宠物
        </div>

        <div v-else class="result-list">
          <RouterLink
            v-for="item in result.items"
            :key="item.pet_name"
            class="result-item"
            :to="`/pokemon/${encodeURIComponent(item.pet_name)}`"
          >
            {{ item.pet_name }}
          </RouterLink>
        </div>
      </section>

      <section v-else-if="!loading && !hasSearched" class="card tip-card">
        <h2 class="section-title">使用说明</h2>
        <ul class="tip-list">
          <li>按数据库里的身高区间（cm）和体重区间（g）同时匹配。</li>
          <li>只有同时满足身高和体重条件的宠物才会返回。</li>
          <li>结果已按名称去重，避免同一宠物重复出现。</li>
        </ul>
      </section>
    </main>
  </div>
</template>

<style scoped>
.body-match-page {
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

.back-btn,
.theme-btn,
.submit-btn {
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

.back-btn:hover,
.submit-btn:hover {
  background: var(--color-hover);
}

.page-title {
  flex: 1;
  margin: 0;
  font-size: 22px;
  color: var(--color-accent);
}

.theme-btn {
  padding: 8px 16px;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
}

.theme-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.page-main {
  max-width: 980px;
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

.helper-text,
.result-summary {
  margin: 0 0 16px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-muted);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-label {
  font-size: 14px;
  color: var(--color-text);
}

.field-input {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 14px;
  box-sizing: border-box;
  outline: none;
}

.field-input:focus {
  border-color: var(--color-accent);
}

.actions {
  margin-top: 18px;
}

.submit-btn {
  padding: 10px 20px;
  border: 1px solid var(--color-accent);
  background: transparent;
  color: var(--color-accent);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-msg {
  margin-bottom: 20px;
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  color: #f87171;
}

.empty-msg {
  padding: 24px 0 8px;
  color: var(--color-muted);
  text-align: center;
}

.result-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.result-item {
  padding: 14px 16px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-bg);
  color: var(--color-text);
  text-decoration: none;
  transition: all 0.2s ease;
}

.result-item:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.tip-list {
  margin: 0;
  padding-left: 20px;
  color: var(--color-muted);
  line-height: 1.8;
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

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
