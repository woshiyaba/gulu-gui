<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { fetchChronology } from '@/api/pokemon'
import type { ChronologyListItem } from '@/types/pokemon'

const loading = ref(false)
const error = ref('')
const items = ref<ChronologyListItem[]>([])
const hasLoaded = ref(false)

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const list = await fetchChronology()
    items.value = list ?? []
    hasLoaded.value = true
  } catch {
    error.value = '加载失败，请稍后再试'
    items.value = []
    hasLoaded.value = true
  } finally {
    loading.value = false
  }
}

function goDetail(id: number) {
  uni.navigateTo({ url: `/pages/more/chronology-detail?id=${id}` })
}

onLoad(() => {
  void loadData()
})
</script>

<template>
  <view class="page">
    <view class="hero-card">
      <text class="hero-title">洛克纪年</text>
      <text class="hero-subtitle">沿着时间脉络，回顾洛克王国的大事记。</text>
    </view>

    <view v-if="error" class="error-box">
      <text>{{ error }}</text>
    </view>

    <view v-if="loading && !hasLoaded" class="skeleton-list">
      <view v-for="n in 5" :key="n" class="skeleton-card" />
    </view>

    <view v-else-if="items.length === 0 && hasLoaded && !error" class="empty-box">
      <text class="empty-title">暂无大事记</text>
      <text class="empty-tip">敬请期待</text>
    </view>

    <view v-else class="timeline">
      <view
        v-for="(item, index) in items"
        :key="item.id"
        class="tl-item"
        :class="index % 2 === 0 ? 'tl-item--left' : 'tl-item--right'"
      >
        <view class="tl-node" />
        <view class="tl-card" @tap="goDetail(item.id)">
          <text class="tl-date">{{ item.event_date }}</text>
          <image
            v-if="item.cover_image"
            class="tl-image"
            :src="item.cover_image"
            mode="aspectFill"
          />
          <text class="tl-title">{{ item.title || '（无标题）' }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 24rpx;
  background: linear-gradient(180deg, #f3f8ff 0%, #f9fbff 100%);
}

.hero-card {
  margin-bottom: 28rpx;
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

.error-box {
  margin-bottom: 24rpx;
  padding: 28rpx;
  border-radius: 28rpx;
  color: #c74646;
  background: #fff2f2;
  box-shadow: 0 12rpx 32rpx rgba(64, 125, 255, 0.08);
}

.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.skeleton-card {
  height: 160rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #edf4ff 0%, #ffffff 100%);
}

.empty-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12rpx;
  padding: 80rpx 36rpx;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 12rpx 32rpx rgba(64, 125, 255, 0.08);
}

.empty-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #284974;
}

.empty-tip {
  font-size: 24rpx;
  color: #7a93bb;
}

/* 时间树：中间一条竖线，事件左右交错分布 */
.timeline {
  position: relative;
  padding: 16rpx 0;
}

.timeline::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 4rpx;
  margin-left: -2rpx;
  background: linear-gradient(180deg, #8ab8ff 0%, #2b74ff 100%);
  border-radius: 4rpx;
}

.tl-item {
  position: relative;
  display: flex;
  margin-bottom: 24rpx;
}

.tl-item--left {
  justify-content: flex-start;
}

.tl-item--right {
  justify-content: flex-end;
}

/* 中轴上的节点圆点 */
.tl-node {
  position: absolute;
  top: 20rpx;
  left: 50%;
  width: 18rpx;
  height: 18rpx;
  margin-left: -9rpx;
  border-radius: 50%;
  background: #2b74ff;
  border: 3rpx solid #ffffff;
  box-shadow: 0 0 0 3rpx rgba(43, 116, 255, 0.18);
  z-index: 1;
}

.tl-card {
  width: 40%;
  padding: 14rpx;
  border-radius: 18rpx;
  background: #ffffff;
  box-shadow: 0 8rpx 24rpx rgba(64, 125, 255, 0.08);
}

.tl-date {
  display: block;
  font-size: 22rpx;
  font-weight: 700;
  color: #2b74ff;
}

.tl-image {
  display: block;
  width: 100%;
  height: 130rpx;
  margin-top: 8rpx;
  border-radius: 12rpx;
  background: #f3f8ff;
}

.tl-title {
  display: block;
  margin-top: 8rpx;
  font-size: 24rpx;
  font-weight: 600;
  line-height: 1.45;
  color: #1f3760;
  word-break: break-word;
}
</style>
