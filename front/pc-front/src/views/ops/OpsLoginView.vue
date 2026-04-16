<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { loginOps, saveOpsToken } from '@/api/ops'

const router = useRouter()
const username = ref('admin')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function onSubmit() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const res = await loginOps(username.value.trim(), password.value)
    saveOpsToken(res.access_token)
    await router.replace('/ops/home')
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="ops-login-page">
    <div class="bg-decoration bg-decoration-a"></div>
    <div class="bg-decoration bg-decoration-b"></div>
    <form class="ops-login-card" @submit.prevent="onSubmit">
      <div class="login-head">
        <span class="badge">内部使用</span>
        <h1>运营维护平台</h1>
      </div>

      <label>
        <span>账号</span>
        <input v-model="username" type="text" placeholder="请输入账号" />
      </label>

      <label>
        <span>密码</span>
        <input v-model="password" type="password" placeholder="请输入密码" />
      </label>

      <p v-if="error" class="error">{{ error }}</p>
      <button type="submit" class="submit-btn" :disabled="loading">
        {{ loading ? '登录中...' : '进入后台' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.ops-login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  position: relative;
  overflow: hidden;
}

.bg-decoration {
  position: absolute;
  border-radius: 999px;
  filter: blur(10px);
  opacity: 0.5;
  pointer-events: none;
}

.bg-decoration-a {
  width: 320px;
  height: 320px;
  background: rgba(37, 99, 235, 0.18);
  top: 8%;
  left: 8%;
}

.bg-decoration-b {
  width: 260px;
  height: 260px;
  background: rgba(124, 147, 255, 0.2);
  right: 10%;
  bottom: 12%;
}

.ops-login-card {
  width: min(100%, 420px);
  background: color-mix(in srgb, var(--color-surface) 90%, white 10%);
  border: 1px solid color-mix(in srgb, var(--color-border) 78%, white 22%);
  border-radius: 24px;
  padding: 28px;
  box-shadow: 0 24px 60px rgba(37, 99, 235, 0.14);
  backdrop-filter: blur(14px);
  display: grid;
  gap: 16px;
  position: relative;
  z-index: 1;
}

.login-head {
  display: grid;
  gap: 8px;
}

.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  background: var(--color-tag-bg);
  color: var(--color-accent);
  font-size: 12px;
  font-weight: 700;
}

h1 {
  font-size: 28px;
}

p {
  color: var(--color-muted);
}

label {
  display: grid;
  gap: 8px;
}

input {
  height: 46px;
  border: 1px solid color-mix(in srgb, var(--color-border) 84%, white 16%);
  border-radius: 12px;
  background: color-mix(in srgb, var(--color-bg) 82%, white 18%);
  color: var(--color-text);
  padding: 0 14px;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12);
}

.submit-btn {
  height: 46px;
  border: none;
  border-radius: 12px;
  background: var(--color-accent);
  color: #fff;
  cursor: pointer;
  font-weight: 700;
  box-shadow: 0 14px 28px rgba(37, 99, 235, 0.26);
  transition: transform 0.18s ease, opacity 0.18s ease;
}

.submit-btn:hover {
  transform: translateY(-1px);
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: wait;
}

.error {
  color: #dc2626;
  background: rgba(220, 38, 38, 0.08);
  border: 1px solid rgba(220, 38, 38, 0.16);
  border-radius: 12px;
  padding: 10px 12px;
}

</style>
