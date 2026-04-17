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
    <section class="table-card">
      <div class="toolbar">
        <button type="button" class="btn-primary" @click="openModal">新增用户</button>
        <div class="toolbar-meta">共 {{ users.length }} 人</div>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
      <div v-if="loading" class="table-placeholder">加载中...</div>
      <div v-else-if="!users.length" class="table-placeholder">暂无用户</div>

      <div v-else class="table-wrap">
        <table class="user-table">
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
                <div class="actions">
                  <button type="button" class="text-btn" @click="openEditModal(item)">修改</button>
                  <button
                    type="button"
                    class="text-btn danger"
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

    <div v-if="modalVisible" class="modal-mask" @click="closeModal">
      <section class="modal" @click.stop>
        <div class="modal-head">
          <h3>{{ editingId ? '编辑用户' : '新增用户' }}</h3>
          <button type="button" class="btn-text" @click="closeModal">关闭</button>
        </div>
        <form class="form-grid" @submit.prevent="submit">
          <label class="form-row">
            <span>账号</span>
            <input
              v-model="form.username"
              :disabled="!!editingId"
              required
              type="text"
              :placeholder="editingId ? '' : '至少 3 位'"
            />
          </label>
          <label class="form-row">
            <span>昵称</span>
            <input v-model="form.nickname" type="text" placeholder="为空则默认同账号" />
          </label>
          <label class="form-row">
            <span>密码</span>
            <input
              v-model="form.password"
              :required="!editingId"
              type="password"
              :placeholder="editingId ? '不修改请留空' : '至少 6 位'"
            />
          </label>
          <label class="form-row">
            <span>角色</span>
            <select v-model="form.role">
              <option value="editor">editor</option>
              <option value="admin">admin</option>
            </select>
          </label>
          <div class="modal-actions">
            <button type="submit" class="btn-primary" :disabled="saving">
              {{ saving ? (editingId ? '保存中...' : '创建中...') : editingId ? '保存' : '创建' }}
            </button>
            <button type="button" class="btn-secondary" @click="closeModal">取消</button>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>

<style scoped>
.ops-page { display: grid; gap: 16px; }
.table-card { background: #fff; border: 1px solid #ebeef5; border-radius: 4px; padding: 16px 20px; }
.toolbar { display: flex; justify-content: space-between; margin-bottom: 12px; }
.toolbar-meta { color: #909399; font-size: 13px; }
.table-wrap { border: 1px solid #ebeef5; border-radius: 2px; overflow: auto; }
.user-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.user-table th, .user-table td { border-bottom: 1px solid #ebeef5; border-right: 1px solid #ebeef5; padding: 10px 12px; text-align: center; }
.user-table th:last-child, .user-table td:last-child { border-right: none; }
.user-table thead { background: #fafafa; }
.actions { display: inline-flex; align-items: center; justify-content: center; gap: 12px; }
.text-btn { border: none; background: transparent; color: #409eff; cursor: pointer; font-size: 13px; padding: 0; }
.text-btn:hover { color: #66b1ff; }
.text-btn.danger { color: #f56c6c; }
.text-btn.danger:hover { color: #f78989; }
.text-btn:disabled, .text-btn.danger:disabled { color: #c0c4cc; cursor: not-allowed; }
.table-placeholder { min-height: 160px; display: grid; place-items: center; color: #909399; border: 1px dashed #dcdfe6; border-radius: 2px; }
.error { color: #dc2626; background: #fef0f0; border: 1px solid #fde2e2; border-radius: 4px; padding: 10px 12px; margin-bottom: 10px; }

.modal-mask { position: fixed; inset: 0; display: grid; place-items: center; background: rgba(15, 23, 42, 0.34); padding: 24px; z-index: 1000; }
.modal { width: min(100%, 640px); background: #fff; border: 1px solid #ebeef5; border-radius: 4px; padding: 0; }
.modal-head { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px 16px; padding: 0 20px 20px; }
.form-row { display: grid; grid-template-columns: 64px minmax(0, 1fr); align-items: center; gap: 10px; }
.form-row span { font-size: 13px; color: #606266; }
.form-row input, .form-row select { height: 36px; border: 1px solid #dcdfe6; border-radius: 4px; padding: 0 12px; }
.modal-actions { grid-column: 1 / -1; display: flex; justify-content: center; gap: 10px; padding-top: 8px; }
.btn-primary, .btn-secondary { height: 36px; border-radius: 4px; padding: 0 14px; cursor: pointer; }
.btn-primary { background: #409eff; border: 1px solid #409eff; color: #fff; }
.btn-secondary { background: #fff; border: 1px solid #dcdfe6; color: #606266; }
.btn-text { border: none; background: transparent; color: #909399; cursor: pointer; }

@media (max-width: 960px) {
  .form-grid { grid-template-columns: 1fr; }
  .form-row { grid-template-columns: 1fr; }
}
</style>
