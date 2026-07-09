<script setup lang="ts">
import { computed, ref } from 'vue'
import { submitFeedback } from '@/api/feedback'

const TYPE_OPTIONS = ['功能建议', '问题反馈', '数据纠错', '其他']
const MAX_LEN = 2000

const content = ref('')
const feedbackType = ref('')
const submitting = ref(false)

const remaining = computed(() => MAX_LEN - content.value.length)
const canSubmit = computed(() => content.value.trim().length > 0 && !submitting.value)

function selectType(type: string) {
  feedbackType.value = feedbackType.value === type ? '' : type
}

async function handleSubmit() {
  const text = content.value.trim()
  if (!text) {
    uni.showToast({ title: '请填写反馈内容', icon: 'none' })
    return
  }

  submitting.value = true
  try {
    await submitFeedback({
      content: text,
      feedback_type: feedbackType.value || undefined,
    })
    uni.showToast({ title: '提交成功，感谢反馈！', icon: 'success' })
    content.value = ''
    feedbackType.value = ''
    setTimeout(() => uni.navigateBack(), 1200)
  } catch (error) {
    const message = error instanceof Error ? error.message : '提交失败，请稍后再试'
    uni.showToast({ title: message, icon: 'none' })
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <view class="page">
    <view class="hero-card">
      <text class="hero-title">意见反馈</text>
      <text class="hero-subtitle">你的建议会帮助我们做得更好。</text>
    </view>

    <view class="form-card">
      <text class="label">反馈类型</text>
      <view class="type-list">
        <view
          v-for="type in TYPE_OPTIONS"
          :key="type"
          class="type-chip"
          :class="{ active: feedbackType === type }"
          @tap="selectType(type)"
        >
          <text class="type-text">{{ type }}</text>
        </view>
      </view>

      <text class="label">反馈内容</text>
      <textarea
        v-model="content"
        class="content-input"
        placeholder="请详细描述你遇到的问题或建议……"
        :maxlength="MAX_LEN"
        auto-height
      />
      <text class="counter">{{ remaining }}</text>
    </view>

    <button class="submit-btn" :disabled="!canSubmit" :loading="submitting" @tap="handleSubmit">
      提交反馈
    </button>
  </view>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 24rpx;
  background: linear-gradient(180deg, #f3f8ff 0%, #f9fbff 100%);
}

.hero-card {
  margin-bottom: 24rpx;
  padding: 36rpx 28rpx;
  border-radius: 28rpx;
  background: linear-gradient(135deg, #2b74ff 0%, #53a0ff 100%);
  box-shadow: 0 12rpx 32rpx rgba(43, 116, 255, 0.2);
}

.hero-title {
  display: block;
  font-size: 40rpx;
  font-weight: 700;
  color: #ffffff;
}

.hero-subtitle {
  display: block;
  margin-top: 10rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.8);
}

.form-card {
  padding: 28rpx;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 8rpx 24rpx rgba(64, 125, 255, 0.06);
}

.label {
  display: block;
  margin: 18rpx 0 14rpx;
  font-size: 28rpx;
  font-weight: 700;
  color: #214887;
}
.label:first-child {
  margin-top: 0;
}

.type-list {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}

.type-chip {
  padding: 12rpx 28rpx;
  border-radius: 999rpx;
  background: #f0f5ff;
  border: 2rpx solid transparent;
}
.type-chip.active {
  background: #e4efff;
  border-color: #2b74ff;
}
.type-text {
  font-size: 26rpx;
  color: #5a76a8;
}
.type-chip.active .type-text {
  color: #2b74ff;
  font-weight: 700;
}

.content-input {
  width: 100%;
  min-height: 220rpx;
  padding: 20rpx;
  box-sizing: border-box;
  border-radius: 16rpx;
  background: #f7faff;
  font-size: 28rpx;
  line-height: 1.6;
  color: #1f3760;
}

.counter {
  display: block;
  margin-top: 8rpx;
  text-align: right;
  font-size: 22rpx;
  color: #b5c8e8;
}

.submit-btn {
  margin-top: 32rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #2b74ff 0%, #53a0ff 100%);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 700;
  box-shadow: 0 12rpx 28rpx rgba(43, 116, 255, 0.22);
}
.submit-btn[disabled] {
  opacity: 0.5;
  box-shadow: none;
}
</style>
