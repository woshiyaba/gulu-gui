<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { fetchPokemonMarks } from '@/api/pokemon'
import type { PokemonMark } from '@/types/pokemon'

const keyword = ref('')
const loading = ref(false)
const error = ref('')
const marks = ref<PokemonMark[]>([])
const hasLoaded = ref(false)

const filteredMarks = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  const list = [...marks.value].sort((a, b) => a.sort_order - b.sort_order)
  if (!kw) return list
  return list.filter((item) => item.zh_name.toLowerCase().includes(kw))
})

const summaryText = computed(() => {
  if (!hasLoaded.value) return ''
  if (keyword.value.trim()) {
    return `关键词"${keyword.value.trim()}"共匹配到 ${filteredMarks.value.length} 条词条`
  }
  return `当前共收录 ${marks.value.length} 条词条`
})

async function loadMarks() {
  loading.value = true
  error.value = ''
  try {
    const list = await fetchPokemonMarks()
    marks.value = list ?? []
    hasLoaded.value = true
  } catch {
    error.value = '查询失败，请稍后再试'
    marks.value = []
    hasLoaded.value = true
  } finally {
    loading.value = false
  }
}

onLoad(() => {
  void loadMarks()
})
</script>

<template>
  <view class="page">
    <view class="search-card">
      <text class="page-title">名词解释</text>
      <text class="page-subtitle">印记、状态、增益、减益、环境等战斗术语的详细说明。</text>
      <view class="search-box">
        <input
          v-model="keyword"
          class="search-input"
          confirm-type="search"
          placeholder="按名字搜索，例如：印记、中毒、雨天"
        />
      </view>
    </view>

    <view v-if="hasLoaded" class="summary-row">
      <text class="summary-text">{{ summaryText }}</text>
    </view>

    <view v-if="error" class="error-box">
      <text>{{ error }}</text>
    </view>

    <view v-if="loading && !hasLoaded" class="skeleton-list">
      <view v-for="n in 6" :key="n" class="skeleton-card" />
    </view>

    <view
      v-else-if="filteredMarks.length === 0 && hasLoaded && !error"
      class="empty-box"
    >
      <text class="empty-title">没有找到匹配的词条</text>
      <text class="empty-tip">试试换个关键词</text>
    </view>

    <view v-else class="mark-list">
      <view v-for="item in filteredMarks" :key="item.id" class="mark-card">
        <view class="mark-icon-wrap">
          <image
            v-if="item.image"
            class="mark-icon"
            :src="item.image"
            mode="aspectFit"
          />
          <view v-else class="mark-icon-placeholder">
            {{ item.zh_name.slice(0, 1) }}
          </view>
        </view>
        <view class="mark-body">
          <text class="mark-name">{{ item.zh_name }}</text>
          <text class="mark-desc">{{ item.zh_description }}</text>
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

.search-card,
.empty-box,
.error-box {
  margin-bottom: 24rpx;
  padding: 28rpx;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 12rpx 32rpx rgba(64, 125, 255, 0.08);
}

.page-title {
  display: block;
  font-size: 36rpx;
  font-weight: 700;
  color: #1f4ea3;
}

.page-subtitle {
  display: block;
  margin-top: 10rpx;
  font-size: 24rpx;
  line-height: 1.6;
  color: #5f7da6;
}

.search-box {
  margin-top: 24rpx;
  padding: 0 24rpx;
  border-radius: 999rpx;
  background: #f3f8ff;
}

.search-input {
  height: 78rpx;
  font-size: 28rpx;
  color: #1e3557;
}

.summary-row {
  margin-bottom: 20rpx;
}

.summary-text {
  font-size: 24rpx;
  color: #7a93bb;
}

.error-box {
  color: #c74646;
  background: #fff2f2;
}

.empty-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12rpx;
  padding: 80rpx 36rpx;
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

.mark-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.mark-card {
  display: flex;
  align-items: flex-start;
  gap: 20rpx;
  padding: 28rpx;
  border-radius: 24rpx;
  background: #ffffff;
  box-shadow: 0 8rpx 24rpx rgba(64, 125, 255, 0.06);
}

.mark-icon-wrap {
  width: 88rpx;
  height: 88rpx;
  border-radius: 20rpx;
  background: #f3f8ff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.mark-icon {
  width: 72rpx;
  height: 72rpx;
}

.mark-icon-placeholder {
  font-size: 36rpx;
  font-weight: 700;
  color: #8ab0ff;
}

.mark-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.mark-name {
  font-size: 30rpx;
  font-weight: 700;
  color: #1f3760;
}

.mark-desc {
  font-size: 24rpx;
  line-height: 1.7;
  color: #6f89b2;
  word-break: break-word;
}
</style>
