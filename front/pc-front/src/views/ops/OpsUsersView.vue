<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  clearOpsToken,
  createOpsUser,
  deleteOpsUser,
  fetchOpsMe,
  fetchOpsUsers,
  showOpsToast,
  updateOpsUser,
  type OpsUser,
} from '@/api/ops'

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const users = ref<OpsUser[]>([])
const modalVisible = ref(false)
const editingId = ref<number | null>(null)
const currentUserId = ref<number | null>(null)

const form = reactive({
  username: '',
  nickname: '',
  password: '',
  role: 'editor' as 'editor' | 'admin',
})

function resetForm() {
  form.username = ''
  form.nickname = ''
  form.password = ''
  form.role = 'editor'
}

function openModal() {
  editingId.value = null
  resetForm()
  modalVisible.value = true
}

function openEditModal(user: OpsUser) {
  editingId.value = user.id
  form.username = user.username
  form.nickname = user.nickname
  form.password = ''
  form.role = user.role
  modalVisible.value = true
}

function closeModal() {
  modalVisible.value = false
}

async function loadUsers() {
  loading.value = true
  error.value = ''
  try {
    const [me, result] = await Promise.all([fetchOpsMe(), fetchOpsUsers()])
    currentUserId.value = me.id
    users.value = result.items
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

async function submit() {
  if (saving.value) return
  saving.value = true
  error.value = ''
  try {
    if (editingId.value) {
      await updateOpsUser(editingId.value, {
        nickname: form.nickname.trim(),
        password: form.password || undefined,
        role: form.role,
      })
      showOpsToast('用户已更新', 'success')
    } else {
      await createOpsUser({
        username: form.username.trim(),
        nickname: form.nickname.trim(),
        password: form.password,
        role: form.role,
      })
      showOpsToast('用户创建成功', 'success')
    }
    closeModal()
    await loadUsers()
  } catch (err: any) {
    error.value = err?.response?.data?.detail || (editingId.value ? '更新失败' : '创建失败')
    showOpsToast(error.value, 'error')
  } finally {
    saving.value = false
  }
}

async function removeUser(user: OpsUser) {
  if (!window.confirm(`确定删除用户 ${user.username} 吗？`)) return
  try {
    await deleteOpsUser(user.id)
    showOpsToast('用户已删除', 'success')
    await loadUsers()
  } catch (err: any) {
    const detail = err?.response?.data?.detail || '删除失败'
    showOpsToast(detail, 'error')
  }
}

onMounted(() => {
  void loadUsers()
})
</script>

<template>
  <div class="ops-page">
    <section class="ops-card-padded">
      <div class="ops-toolbar">
        <button type="button" class="ops-btn ops-btn-primary" @click="openModal">新增用户</button>
        <span class="ops-toolbar-meta">共 {{ users.length }} 人</span>
      </div>

      <p v-if="error" class="ops-error">{{ error }}</p>
      <div v-if="loading" class="ops-loading">加载中...</div>
      <div v-else-if="!users.length" class="ops-empty"><strong>暂无用户</strong></div>

      <div v-else class="ops-table-wrap">
        <table class="ops-table">
          <thead>
            <tr>
              <th>序号</th>
              <th>账号</th>
              <th>昵称</th>
              <th>角色</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in users" :key="item.id">
              <td>{{ index + 1 }}</td>
              <td>{{ item.username }}</td>
              <td>{{ item.nickname }}</td>
              <td>{{ item.role }}</td>
              <td>
                <div class="ops-action-group">
                  <button type="button" class="ops-btn ops-btn-text" @click="openEditModal(item)">修改</button>
                  <button
                    type="button"
                    class="ops-btn ops-btn-text ops-btn--danger"
                    :disabled="item.id === currentUserId"
                    @click="removeUser(item)"
                  >
                    删除
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div v-if="modalVisible" class="ops-modal-mask" @click="closeModal">
      <section class="ops-modal" @click.stop>
        <div class="ops-modal-header">
          <h3>{{ editingId ? '编辑用户' : '新增用户' }}</h3>
          <button type="button" class="ops-modal-close" @click="closeModal">✕</button>
        </div>
        <form @submit.prevent="submit">
          <div class="ops-modal-body">
            <div class="ops-form-grid">
              <label class="ops-form-item">
                <span>账号</span>
                <input
                  v-model="form.username"
                  :disabled="!!editingId"
                  required
                  type="text"
                  :placeholder="editingId ? '' : '至少 3 位'"
                  class="ops-input"
                />
              </label>
              <label class="ops-form-item">
                <span>昵称</span>
                <input v-model="form.nickname" type="text" placeholder="为空则默认同账号" class="ops-input" />
              </label>
              <label class="ops-form-item">
                <span>密码</span>
                <input
                  v-model="form.password"
                  :required="!editingId"
                  type="password"
                  :placeholder="editingId ? '不修改请留空' : '至少 6 位'"
                  class="ops-input"
                />
              </label>
              <label class="ops-form-item">
                <span>角色</span>
                <select v-model="form.role" class="ops-select">
                  <option value="editor">editor</option>
                  <option value="admin">admin</option>
                </select>
              </label>
            </div>
          </div>
          <div class="ops-modal-footer">
            <button type="submit" class="ops-btn ops-btn-primary" :disabled="saving">
              {{ saving ? (editingId ? '保存中...' : '创建中...') : editingId ? '保存' : '创建' }}
            </button>
            <button type="button" class="ops-btn ops-btn-secondary" @click="closeModal">取消</button>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>
