<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { OPS_TOAST_EVENT, clearOpsToken, fetchOpsMe, showOpsToast, updateOpsMe, type OpsUser } from '@/api/ops'

const route = useRoute()
const router = useRouter()
const user = ref<OpsUser | null>(null)
const profileVisible = ref(false)
const userMenuVisible = ref(false)
const sidebarCollapsed = ref(false)
const profileSaving = ref(false)
const profileError = ref('')
const profileSuccess = ref('')
const profileForm = reactive({
  nickname: '',
  current_password: '',
  new_password: '',
})
const nicknameInputRef = ref<HTMLInputElement | null>(null)
const toasts = ref<Array<{ id: number; message: string; type: 'success' | 'error' | 'info' }>>([])

const menus = [
  { to: '/ops/home', label: '首页' },
  { to: '/ops/dicts', label: '字典维护' },
  { to: '/ops/users', label: '用户管理' },
  { to: '/ops/pokemon', label: '精灵维护' },
  { to: '/ops/evolution-chains', label: '进化链维护' },
  { to: '/ops/banners', label: 'Banner管理' },
  { to: '/ops/pokemon-lineups', label: '阵容管理' },
  { to: '/ops/skills', label: '技能维护' },
  { to: '/ops/skill-stones', label: '技能石维护' },
  { to: '/ops/personalities', label: '性格维护' },
  { to: '/ops/marks', label: '印记维护' },
  { to: '/ops/resonance-magic', label: '共鸣魔法' },
  { to: '/ops/pokemon-marks', label: '名词解释' },
  { to: '/ops/map', label: '地图维护', disabled: true },
]

const primaryMenus = computed(() => menus.slice(0, 1))
const maintainMenus = computed(() => menus.slice(1))

const pageTitle = computed(() => {
  const current = menus.find((item) => route.path === item.to)
  return current?.label || '运营维护平台'
})

function resetProfileForm() {
  profileError.value = ''
  profileSuccess.value = ''
  if (user.value) {
    profileForm.nickname = user.value.nickname || user.value.username
  }
  profileForm.current_password = ''
  profileForm.new_password = ''
}

async function loadMe() {
  try {
    user.value = await fetchOpsMe()
    profileForm.nickname = user.value.nickname || user.value.username
  } catch {
    clearOpsToken()
    await router.replace('/ops/login')
  }
}

function toggleProfile() {
  profileVisible.value = !profileVisible.value
  userMenuVisible.value = false
  resetProfileForm()
  if (profileVisible.value) {
    void nextTick(() => nicknameInputRef.value?.focus())
  }
}

function closeProfile() {
  profileVisible.value = false
  resetProfileForm()
}

function toggleUserMenu() {
  userMenuVisible.value = !userMenuVisible.value
}

function closeUserMenu() {
  userMenuVisible.value = false
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function onWindowKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && profileVisible.value) {
    closeProfile()
  }
  if (event.key === 'Escape' && userMenuVisible.value) {
    closeUserMenu()
  }
}

function onWindowClick() {
  if (userMenuVisible.value) {
    closeUserMenu()
  }
}

function pushToast(message: string, type: 'success' | 'error' | 'info' = 'success') {
  const id = Date.now() + Math.random()
  toasts.value.push({ id, message, type })
  window.setTimeout(() => {
    toasts.value = toasts.value.filter((item) => item.id !== id)
  }, 2600)
}

function onToastEvent(event: Event) {
  const customEvent = event as CustomEvent<{ message: string; type: 'success' | 'error' | 'info' }>
  if (!customEvent.detail?.message) return
  pushToast(customEvent.detail.message, customEvent.detail.type || 'success')
}

async function saveProfile() {
  if (!user.value || profileSaving.value) return
  profileSaving.value = true
  profileError.value = ''
  profileSuccess.value = ''
  try {
    const updated = await updateOpsMe({
      nickname: profileForm.nickname.trim(),
      current_password: profileForm.current_password,
      new_password: profileForm.new_password,
    })
    user.value = updated
    profileForm.current_password = ''
    profileForm.new_password = ''
    profileSuccess.value = '个人信息已更新'
    showOpsToast('个人信息已更新', 'success')
    window.setTimeout(() => {
      if (profileVisible.value) {
        closeProfile()
      }
    }, 500)
  } catch (err: any) {
    profileError.value = err?.response?.data?.detail || '保存失败'
  } finally {
    profileSaving.value = false
  }
}

function logout() {
  closeUserMenu()
  clearOpsToken()
  void router.replace('/ops/login')
}

onMounted(() => {
  window.addEventListener('keydown', onWindowKeydown)
  window.addEventListener('click', onWindowClick)
  window.addEventListener(OPS_TOAST_EVENT, onToastEvent as EventListener)
  void loadMe()
})

onUnmounted(() => {
  window.removeEventListener('keydown', onWindowKeydown)
  window.removeEventListener('click', onWindowClick)
  window.removeEventListener(OPS_TOAST_EVENT, onToastEvent as EventListener)
})
</script>

<template>
  <div class="ops-layout" :class="{ collapsed: sidebarCollapsed }">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-logo">G</div>
        <div class="brand-text">
          <h1>Gulu Ops</h1>
          <p>运营维护平台</p>
        </div>
      </div>

      <nav class="menu">
        <div class="menu-section">
          <div class="menu-group-title">工作台</div>
          <template v-for="item in primaryMenus" :key="item.to">
            <RouterLink
              v-if="!item.disabled"
              :to="item.to"
              class="menu-item"
              :class="{ active: route.path === item.to }"
            >
              <span class="menu-icon"></span>
              {{ item.label }}
            </RouterLink>
            <span v-else class="menu-item disabled">
              <span class="menu-icon"></span>
              {{ item.label }}
            </span>
          </template>
        </div>

        <div class="menu-section">
          <div class="menu-group-title">数据维护</div>
          <template v-for="item in maintainMenus" :key="item.to">
          <RouterLink
            v-if="!item.disabled"
            :to="item.to"
            class="menu-item"
            :class="{ active: route.path === item.to }"
          >
            <span class="menu-icon"></span>
            {{ item.label }}
          </RouterLink>
          <span v-else class="menu-item disabled">
            <span class="menu-icon"></span>
            {{ item.label }}
          </span>
          </template>
        </div>
      </nav>
    </aside>

    <main class="main">
      <header class="topbar">
        <div class="page-meta">
          <button type="button" class="collapse-btn" @click="toggleSidebar">
            <span class="collapse-icon">{{ sidebarCollapsed ? '>' : '<' }}</span>
          </button>
          <h2>{{ pageTitle }}</h2>
        </div>
        <div class="userbox">
          <div v-if="user" class="user-dropdown" @click.stop>
            <button type="button" class="user-trigger" @click="toggleUserMenu">
              <span class="avatar">{{ (user.nickname || user.username).slice(0, 1).toUpperCase() }}</span>
              <span class="user-meta">
                <strong>{{ user.nickname || user.username }}</strong>
                <small>{{ user.role }}</small>
              </span>
              <span class="caret" :class="{ open: userMenuVisible }"></span>
            </button>

            <div v-if="userMenuVisible" class="user-menu">
              <button type="button" class="user-menu-item" @click="toggleProfile">个人信息</button>
              <button type="button" class="user-menu-item danger-text" @click="logout">退出登录</button>
            </div>
          </div>
        </div>
      </header>

      <section class="content-shell">
        <section class="content">
          <RouterView />
        </section>
      </section>
    </main>
  </div>

  <div class="toast-stack" aria-live="polite">
    <div v-for="toast in toasts" :key="toast.id" class="toast" :class="toast.type">
      {{ toast.message }}
    </div>
  </div>

  <div v-if="profileVisible && user" class="modal-mask">
    <section class="profile-modal" @click.stop>
      <div class="profile-header">
        <h3>个人信息</h3>
      </div>

      <div class="profile-grid">
        <label>
          <span>账号</span>
          <input :value="user.username" type="text" disabled />
        </label>
        <label>
          <span>角色</span>
          <input :value="user.role" type="text" disabled />
        </label>
        <label class="full">
          <span>昵称</span>
          <input ref="nicknameInputRef" v-model="profileForm.nickname" type="text" placeholder="请输入昵称" />
        </label>
        <label>
          <span>当前密码</span>
          <input
            v-model="profileForm.current_password"
            type="password"
            placeholder="修改密码时填写"
          />
        </label>
        <label>
          <span>新密码</span>
          <input
            v-model="profileForm.new_password"
            type="password"
            placeholder="不修改可留空"
          />
        </label>
      </div>

      <p v-if="profileError" class="error">{{ profileError }}</p>
      <p v-if="profileSuccess" class="success">{{ profileSuccess }}</p>

      <div class="profile-actions">
        <button type="button" class="btn-primary" @click="saveProfile">
          {{ profileSaving ? '保存中...' : '保存更改' }}
        </button>
        <button type="button" class="btn-secondary" @click="closeProfile">取消</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.ops-layout {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 256px 1fr;
  background: #f5f7fb;
  transition: grid-template-columns 0.2s ease;
}

.ops-layout.collapsed {
  grid-template-columns: 76px 1fr;
}

.sidebar {
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  background: linear-gradient(180deg, #304156 0%, #263445 100%);
  color: #dfe6ee;
  padding: 0;
  display: grid;
  align-content: start;
  gap: 0;
}

.brand {
  min-height: 64px;
  padding: 0 18px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(0, 0, 0, 0.14);
}

.ops-layout.collapsed .brand {
  padding: 0 10px;
  justify-content: center;
}

.brand-logo {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  display: grid;
  place-items: center;
  font-weight: 800;
  box-shadow: 0 6px 18px rgba(64, 158, 255, 0.28);
}

.brand-text h1 {
  font-size: 18px;
  line-height: 1.1;
  color: #fff;
}

.brand-text p {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(223, 230, 238, 0.72);
}

.ops-layout.collapsed .brand-text,
.ops-layout.collapsed .menu-group-title,
.ops-layout.collapsed .menu-item:not(.disabled) {
  font-size: 0;
}

.ops-layout.collapsed .brand-text {
  display: none;
}

.ops-layout.collapsed .menu-item {
  justify-content: center;
  padding: 0;
}

.ops-layout.collapsed .menu-item .menu-icon {
  margin: 0;
}

.menu {
  display: grid;
  gap: 14px;
  padding: 14px 10px;
}

.menu-section {
  display: grid;
  gap: 2px;
}

.menu-group-title {
  padding: 8px 12px 10px;
  font-size: 12px;
  color: rgba(223, 230, 238, 0.52);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  padding: 0 14px;
  border-radius: 6px;
  color: rgba(223, 230, 238, 0.9);
  text-decoration: none;
  border: 1px solid transparent;
  font-weight: 500;
  transition: background-color 0.18s ease, color 0.18s ease;
}

.menu-icon {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: rgba(223, 230, 238, 0.55);
  flex-shrink: 0;
}

.menu-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.menu-item.active {
  position: relative;
  background: #409eff;
  color: #fff;
}

.menu-item.active .menu-icon {
  background: #fff;
}

.menu-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 999px;
  background: #fff;
}

.menu-item.disabled {
  color: rgba(223, 230, 238, 0.44);
  cursor: not-allowed;
}

.main {
  padding: 0;
  display: grid;
  grid-template-rows: 50px 1fr;
  background: #f5f7fb;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  position: sticky;
  top: 0;
  z-index: 20;
  height: 50px;
  padding: 0 18px 0 22px;
  background: #fff;
  border-bottom: 1px solid #e6eaf0;
  backdrop-filter: none;
}

.page-meta {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-meta h2 {
  font-size: 15px;
  line-height: 1.1;
  color: #303133;
  font-weight: 600;
}

.collapse-btn {
  width: 28px;
  height: 28px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #fff;
  color: #606266;
  display: grid;
  place-items: center;
  cursor: pointer;
}

.collapse-btn:hover {
  color: #409eff;
  border-color: #409eff;
}

.collapse-icon {
  font-size: 12px;
  line-height: 1;
  font-weight: 700;
}

.topbar p {
  display: none;
}

.userbox {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.user-dropdown {
  position: relative;
}

.user-trigger {
  height: 38px;
  padding: 0 10px 0 8px;
  border-radius: 19px;
  border: 1px solid transparent;
  background: transparent;
  color: #303133;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: background-color 0.18s ease;
}

.user-trigger:hover {
  background: #f5f7fb;
}

.avatar {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
}

.user-meta {
  display: grid;
  text-align: left;
  line-height: 1.1;
}

.user-meta strong {
  font-size: 13px;
  color: #303133;
}

.user-meta small {
  margin-top: 2px;
  font-size: 11px;
  color: #97a8be;
}

.caret {
  width: 8px;
  height: 8px;
  border-right: 1.5px solid #909399;
  border-bottom: 1.5px solid #909399;
  transform: rotate(45deg);
  transition: transform 0.18s ease;
}

.caret.open {
  transform: rotate(-135deg) translateY(-1px);
}

.user-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  min-width: 160px;
  padding: 6px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e4e7ed;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
}

.user-menu-item {
  width: 100%;
  height: 36px;
  padding: 0 12px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #303133;
  text-align: left;
  cursor: pointer;
}

.user-menu-item:hover {
  background: #f5f7fa;
}

.danger-text {
  color: #f56c6c;
}

.profile-header,
.profile-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.profile-header {
  margin-bottom: 4px;
}

.profile-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 12px;
}

.profile-grid label {
  display: grid;
  gap: 8px;
}

.profile-grid label.full {
  grid-column: 1 / -1;
}

.profile-grid input {
  height: 40px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-bg);
  color: var(--color-text);
  padding: 0 12px;
}

.profile-grid input:disabled {
  opacity: 0.75;
  cursor: not-allowed;
}

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: grid;
  place-items: center;
  padding: 24px;
  z-index: 1000;
}

.toast-stack {
  position: fixed;
  top: 20px;
  right: 20px;
  display: grid;
  gap: 10px;
  z-index: 1100;
}

.toast {
  min-width: 220px;
  max-width: 360px;
  padding: 12px 14px;
  border-radius: 14px;
  color: #fff;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.18);
  backdrop-filter: blur(8px);
}

.toast.success {
  background: linear-gradient(135deg, #16a34a, #22c55e);
}

.toast.error {
  background: linear-gradient(135deg, #dc2626, #ef4444);
}

.toast.info {
  background: linear-gradient(135deg, #2563eb, #3b82f6);
}

.profile-modal {
  width: min(100%, 720px);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 22px;
  padding: 20px;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.24);
  display: grid;
  gap: 16px;
}

.content-shell {
  padding: 16px;
}

.content {
  min-width: 0;
  max-width: 1400px;
  margin: 0 auto;
}

.ghost {
  height: 36px;
  padding: 0 14px;
  border-radius: 4px;
  border: 1px solid #dcdfe6;
  background: transparent;
  color: #606266;
  cursor: pointer;
}

.btn-secondary,
.btn-primary {
  height: 36px;
  min-width: 96px;
  padding: 0 16px;
  border-radius: 4px;
  cursor: pointer;
  transition: transform 0.15s ease, opacity 0.15s ease;
}

.btn-secondary {
  border: 1px solid #dcdfe6;
  background: #fff;
  color: #606266;
}

.btn-primary {
  border: 1px solid transparent;
  background: #409eff;
  color: #fff;
  box-shadow: none;
}

.btn-secondary:hover,
.btn-primary:hover {
  transform: translateY(-1px);
}

.error {
  color: #fff;
  background: #f56c6c;
  border: 1px solid #f56c6c;
  border-radius: 4px;
  padding: 10px 12px;
}

.success {
  color: #fff;
  background: #67c23a;
  border: 1px solid #67c23a;
  border-radius: 4px;
  padding: 10px 12px;
}

@media (max-width: 960px) {
  .ops-layout {
    grid-template-columns: 1fr;
  }

  .sidebar {
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  .menu {
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  }

  .topbar {
    flex-direction: column;
    align-items: flex-start;
    position: static;
    height: auto;
    background: #fff;
    padding: 12px 16px;
    backdrop-filter: none;
  }

  .userbox {
    width: 100%;
    justify-content: flex-start;
  }

  .profile-grid {
    grid-template-columns: 1fr;
  }

  .content {
    max-width: none;
  }

  .content-shell {
    padding: 12px;
  }
}
</style>
