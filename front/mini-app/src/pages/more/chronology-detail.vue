<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { fetchChronologyDetail } from '@/api/pokemon'
import type { ChronologyDetail } from '@/types/pokemon'

const loading = ref(true)
const error = ref('')
const detail = ref<ChronologyDetail | null>(null)

async function loadDetail(id: number) {
  loading.value = true
  error.value = ''
  try {
    detail.value = await fetchChronologyDetail(id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败，请稍后再试'
    detail.value = null
  } finally {
    loading.value = false
  }
}

function previewImage(current: string) {
  if (!detail.value?.images.length) return
  uni.previewImage({
    current,
    urls: detail.value.images,
  })
}

onLoad((options) => {
  const id = Number(options?.id)
  if (!id) {
    error.value = '缺少事件编号，无法加载详情。'
    loading.value = false
    return
  }
  void loadDetail(id)
})
</script>

<template>
  <view class="page">
    <view v-if="loading" class="skeleton-list">
      <view class="skeleton-card" style="height: 120rpx;" />
      <view class="skeleton-card" style="height: 360rpx;" />
    </view>

    <view v-else-if="error" class="error-box">
      <text>{{ error }}</text>
    </view>

    <block v-else-if="detail">
      <view class="head-card">
        <text class="head-date">{{ detail.event_date }}</text>
        <text class="head-title">{{ detail.title || '（无标题）' }}</text>
      </view>

      <view v-if="detail.content" class="content-card">
        <text class="content-text">{{ detail.content }}</text>
      </view>

      <view v-if="detail.images.length" class="image-list">
        <image
          v-for="(url, idx) in detail.images"
          :key="idx"
          class="content-image"
          :src="url"
          mode="widthFix"
          @tap="previewImage(url)"
        />
      </view>
    </block>
  </view>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 24rpx;
  background: linear-gradient(180deg, #f3f8ff 0%, #f9fbff 100%);
}

.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.skeleton-card {
  border-radius: 24rpx;
  background: linear-gradient(135deg, #edf4ff 0%, #ffffff 100%);
}

.error-box {
  padding: 28rpx;
  border-radius: 28rpx;
  color: #c74646;
  background: #fff2f2;
  box-shadow: 0 12rpx 32rpx rgba(64, 125, 255, 0.08);
}

.head-card {
  margin-bottom: 24rpx;
  padding: 36rpx 28rpx;
  border-radius: 28rpx;
  background: linear-gradient(135deg, #2b74ff 0%, #53a0ff 100%);
  box-shadow: 0 12rpx 32rpx rgba(43, 116, 255, 0.2);
}

.head-date {
  display: block;
  font-size: 26rpx;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.85);
}

.head-title {
  display: block;
  margin-top: 10rpx;
  font-size: 40rpx;
  font-weight: 700;
  line-height: 1.4;
  color: #ffffff;
}

.content-card {
  margin-bottom: 24rpx;
  padding: 28rpx;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 8rpx 24rpx rgba(64, 125, 255, 0.06);
}

.content-text {
  font-size: 28rpx;
  line-height: 1.8;
  color: #3a4f72;
  white-space: pre-wrap;
  word-break: break-word;
}

.image-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.content-image {
  width: 100%;
  border-radius: 24rpx;
  background: #f3f8ff;
  box-shadow: 0 8rpx 24rpx rgba(64, 125, 255, 0.06);
}
</style>
