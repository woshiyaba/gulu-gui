<script setup lang="ts">
import { reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import {
  fetchPetPromptExtra,
  savePetPromptExtra,
  type PetPromptExtraField,
} from '@/api/pokemon'
import { getStoredUserId, silentLogin } from '@/utils/auth'

const petId = ref('')
const userId = ref('')
const fields = ref<PetPromptExtraField[]>([])
// code -> 当前输入值
const form = reactive<Record<string, string>>({})

const loading = ref(true)
const saving = ref(false)
const errorTip = ref('')

// 底部下拉选择：当前正在选择的字段 code，空串表示关闭
const pickerCode = ref('')
const pickerOptions = ref<string[]>([])
const pickerTitle = ref('')

function openPicker(field: PetPromptExtraField) {
  pickerCode.value = field.code
  pickerOptions.value = field.options || []
  pickerTitle.value = field.label || '请选择'
}

function closePicker() {
  pickerCode.value = ''
}

function pickOption(value: string) {
  if (pickerCode.value) {
    form[pickerCode.value] = value
  }
  closePicker()
}

async function ensureUserId(): Promise<string> {
  let uid = getStoredUserId()
  if (!uid) {
    await silentLogin()
    uid = getStoredUserId()
  }
  return uid
}

async function loadForm() {
  loading.value = true
  errorTip.value = ''
  try {
    const uid = await ensureUserId()
    if (!uid) {
      errorTip.value = '请先登录后再编辑'
      return
    }
    userId.value = uid
    const res = await fetchPetPromptExtra(Number(petId.value), uid)
    fields.value = res.fields || []
    for (const f of fields.value) {
      form[f.code] = f.value || ''
    }
  } catch (err) {
    errorTip.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function save() {
  if (saving.value) return
  if (!userId.value) {
    uni.showToast({ title: '尚未登录', icon: 'none' })
    return
  }
  saving.value = true
  try {
    const values: Record<string, string> = {}
    for (const f of fields.value) {
      values[f.code] = (form[f.code] || '').trim()
    }
    await savePetPromptExtra({
      user_id: userId.value,
      pet_id: Number(petId.value),
      values,
    })
    uni.showToast({ title: '保存成功', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 600)
  } catch (err) {
    uni.showToast({
      title: err instanceof Error ? err.message : '保存失败',
      icon: 'none',
    })
  } finally {
    saving.value = false
  }
}

onLoad((options) => {
  petId.value = typeof options?.pet_id === 'string' ? options.pet_id : ''
  const rawName = typeof options?.name === 'string' ? options.name : ''
  if (rawName) {
    uni.setNavigationBarTitle({ title: `编辑 · ${decodeURIComponent(rawName)}` })
  }
  if (!petId.value) {
    loading.value = false
    errorTip.value = '缺少宠物信息，无法编辑'
    return
  }
  void loadForm()
})
</script>

<template>
  <view class="page">
    <view v-if="loading" class="hint">加载中…</view>
    <view v-else-if="errorTip" class="hint hint--error">{{ errorTip }}</view>
    <template v-else>
      <view v-if="!fields.length" class="hint">暂无可编辑的字段</view>

      <view v-else class="card">
        <view
          v-for="field in fields"
          :key="field.code"
          class="form-row"
        >
          <text class="form-label">{{ field.label }}</text>
          <!-- 性格等下拉选择 -->
          <view
            v-if="field.type === 'select'"
            class="form-value"
            @tap="openPicker(field)"
          >
            <text :class="['value-text', !form[field.code] ? 'placeholder' : '']">
              {{ form[field.code] || '点击选择' }}
            </text>
            <text class="value-arrow">›</text>
          </view>
          <!-- 自由文本 -->
          <input
            v-else
            v-model="form[field.code]"
            class="form-input"
            type="text"
            :maxlength="50"
            :placeholder="`请输入${field.label}`"
          />
        </view>
      </view>

      <view v-if="fields.length" class="action-bar">
        <view
          class="btn-primary"
          :class="{ 'btn-primary--disabled': saving }"
          @tap="save"
        >
          <text>{{ saving ? '保存中…' : '保存' }}</text>
        </view>
      </view>
    </template>

    <!-- 底部下拉选择弹层 -->
    <view v-if="pickerCode" class="picker-mask" @tap="closePicker">
      <view class="picker-sheet" @tap.stop>
        <view class="picker-head">
          <text class="picker-title">{{ pickerTitle }}</text>
          <text class="picker-close" @tap="closePicker">×</text>
        </view>
        <scroll-view class="picker-list" scroll-y>
          <view class="picker-item" @tap="pickOption('')">
            <text class="picker-item-text">未设置</text>
          </view>
          <view
            v-for="opt in pickerOptions"
            :key="opt"
            class="picker-item"
            @tap="pickOption(opt)"
          >
            <text class="picker-item-text">{{ opt }}</text>
          </view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 24rpx 24rpx 140rpx;
  background: linear-gradient(180deg, #f3f8ff 0%, #f9fbff 100%);
}

.hint {
  margin-top: 120rpx;
  text-align: center;
  font-size: 28rpx;
  color: #9fb1d0;
}

.hint--error {
  color: #c45656;
}

.card {
  background: #ffffff;
  border-radius: 24rpx;
  padding: 8rpx 24rpx;
  box-shadow: 0 8rpx 24rpx rgba(64, 125, 255, 0.06);
}

.form-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 24rpx 0;
  border-bottom: 1rpx solid #f0f4fb;
}

.form-row:last-child {
  border-bottom: none;
}

.form-label {
  flex: 0 0 auto;
  min-width: 150rpx;
  font-size: 28rpx;
  color: #5b7299;
}

.form-input {
  flex: 1;
  min-width: 0;
  font-size: 28rpx;
  color: #1f3760;
  text-align: right;
}

.form-value {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10rpx;
}

.value-text {
  font-size: 28rpx;
  color: #1f3760;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.value-text.placeholder {
  color: #b3c1da;
}

.value-arrow {
  font-size: 32rpx;
  color: #b5c8e8;
}

.action-bar {
  margin-top: 32rpx;
}

.btn-primary {
  height: 88rpx;
  line-height: 88rpx;
  text-align: center;
  border-radius: 20rpx;
  font-size: 30rpx;
  font-weight: 600;
  color: #ffffff;
  background: linear-gradient(135deg, #2b74ff 0%, #5b9aff 100%);
  box-shadow: 0 8rpx 20rpx rgba(43, 116, 255, 0.24);
}

.btn-primary--disabled {
  opacity: 0.6;
}

.picker-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.36);
  z-index: 99;
  display: flex;
  align-items: flex-end;
}

.picker-sheet {
  width: 100%;
  max-height: 86vh;
  background: #ffffff;
  border-top-left-radius: 28rpx;
  border-top-right-radius: 28rpx;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.picker-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx;
  border-bottom: 1rpx solid #f0f4fb;
}

.picker-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #1f3760;
}

.picker-close {
  font-size: 40rpx;
  color: #909bb0;
  padding: 0 16rpx;
}

.picker-list {
  flex: 1;
  max-height: 65vh;
}

.picker-item {
  display: flex;
  align-items: center;
  padding: 22rpx 24rpx;
  border-bottom: 1rpx solid #f6f9fd;
}

.picker-item-text {
  font-size: 28rpx;
  color: #1f3760;
}
</style>
