<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { onLoad, onPullDownRefresh, onReachBottom, onUnload } from '@dcloudio/uni-app'
import { fetchPokemonFruits } from '@/api/pokemon'
import type { PokemonFruit } from '@/types/pokemon'

const keyword = ref('')
const fruits = ref<PokemonFruit[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 30
const loading = ref(false)
const error = ref('')
const hasLoaded = ref(false)

let searchTimer: ReturnType<typeof setTimeout> | undefined

const isInitialLoading = computed(() => loading.value && fruits.value.length === 0)
const hasMore = computed(() => fruits.value.length < total.value)

const COLUMN_COUNT = 4
const columns = computed(() => {
  const cols: PokemonFruit[][] = Array.from({ length: COLUMN_COUNT }, () => [])
  fruits.value.forEach((item, index) => {
    cols[index % COLUMN_COUNT].push(item)
  })
  return cols
})

async function loadFruits(reset = false) {
  if (loading.value) return

  if (reset) {
    currentPage.value = 1
    fruits.value = []
    total.value = 0
  }

  loading.value = true
  error.value = ''

  try {
    const response = await fetchPokemonFruits({
      name: keyword.value.trim() || undefined,
      page: currentPage.value,
      page_size: pageSize,
    })

    fruits.value = reset ? response.items : [...fruits.value, ...response.items]
    total.value = response.total
    hasLoaded.value = true
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败，请稍后再试'
  } finally {
    loading.value = false
    uni.stopPullDownRefresh()
  }
}

async function resetAndLoad() {
  await loadFruits(true)
}

async function loadNextPage() {
  if (loading.value || !hasMore.value || !!error.value) return

  currentPage.value += 1
  await loadFruits()

  if (error.value) {
    currentPage.value -= 1
  }
}

watch(keyword, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    void resetAndLoad()
  }, 300)
})

onLoad(() => {
  void resetAndLoad()
})

onReachBottom(() => {
  void loadNextPage()
})

onPullDownRefresh(() => {
  void resetAndLoad()
})

onUnload(() => {
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<template>
  <view class="page">
    <view class="search-card">
      <text class="page-title">宠物果实查询</text>
      <text class="page-subtitle">查看宠物果实图鉴，按名称筛选你想要的果实。</text>
      <view class="search-box">
        <input
          v-model="keyword"
          class="search-input"
          confirm-type="search"
          placeholder="按名称搜索，例如：蜜瓜、苹果"
        />
      </view>
      <view v-if="hasLoaded" class="summary-row">
        <text class="summary-text" v-if="total > 0">
          已展示 {{ fruits.length }} / {{ total }} 个果实
        </text>
        <text class="summary-text" v-else>未匹配到果实</text>
      </view>
    </view>

    <view v-if="error" class="error-box">
      <text>{{ error }}</text>
    </view>

    <view v-if="isInitialLoading" class="skeleton-grid">
      <view v-for="n in 6" :key="n" class="skeleton-card" />
    </view>

    <view v-else-if="fruits.length === 0 && hasLoaded && !error" class="empty-box">
      <text class="empty-title">没有找到匹配的果实</text>
      <text class="empty-tip">试试换个关键词</text>
    </view>

    <view v-else class="waterfall">
      <view
        v-for="(col, colIndex) in columns"
        :key="colIndex"
        class="waterfall-col"
      >
        <view v-for="item in col" :key="item.id" class="fruit-card">
          <view class="icon-wrap">
            <image
              v-if="item.icon"
              class="fruit-icon"
              :src="item.icon"
              mode="aspectFit"
              lazy-load
            />
            <view v-else class="icon-placeholder">?</view>
          </view>
          <text class="fruit-name">{{ item.name || '未命名' }}</text>
        </view>
      </view>
    </view>

    <view v-if="fruits.length > 0 && !error" class="footer-status">
      <text v-if="loading" class="footer-text">正在加载更多...</text>
      <text v-else-if="hasMore" class="footer-text">继续上滑加载更多</text>
      <text v-else class="footer-text">已经到底啦</text>
    </view>
  </view>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 24rpx;
  background: linear-gradient(180deg, #fff5f8 0%, #fbf8ff 100%);
}

.search-card,
.empty-box,
.error-box {
  margin-bottom: 24rpx;
  padding: 28rpx;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 12rpx 32rpx rgba(255, 107, 156, 0.08);
}

.page-title {
  display: block;
  font-size: 36rpx;
  font-weight: 700;
  color: #c44e7e;
}

.page-subtitle {
  display: block;
  margin-top: 10rpx;
  font-size: 24rpx;
  line-height: 1.6;
  color: #8a6679;
}

.search-box {
  margin-top: 24rpx;
  padding: 0 24rpx;
  border-radius: 999rpx;
  background: #fff0f6;
}

.search-input {
  height: 78rpx;
  font-size: 28rpx;
  color: #4a2435;
}

.summary-row {
  margin-top: 18rpx;
}

.summary-text {
  font-size: 24rpx;
  color: #b08093;
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
  color: #6e3a51;
}

.empty-tip {
  font-size: 24rpx;
  color: #b08093;
}

.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10rpx;
}

.skeleton-card {
  height: 180rpx;
  border-radius: 18rpx;
  background: linear-gradient(135deg, #ffe7f0 0%, #ffffff 100%);
}

.waterfall {
  display: flex;
  gap: 10rpx;
  align-items: flex-start;
}

.waterfall-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}

.fruit-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6rpx;
  padding: 12rpx 8rpx;
  border-radius: 18rpx;
  background: #ffffff;
  box-shadow: 0 8rpx 20rpx rgba(255, 107, 156, 0.08);
}

.icon-wrap {
  width: 100%;
  height: 110rpx;
  border-radius: 14rpx;
  background: linear-gradient(180deg, #fff0f6 0%, #fff8fb 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.fruit-icon {
  width: 90rpx;
  height: 90rpx;
}

.icon-placeholder {
  font-size: 38rpx;
  color: #e7b6c8;
}

.fruit-name {
  width: 100%;
  font-size: 22rpx;
  font-weight: 700;
  color: #4a2435;
  text-align: center;
  line-height: 1.3;
  word-break: break-word;
}

.footer-status {
  display: flex;
  justify-content: center;
  padding: 28rpx 0 16rpx;
}

.footer-text {
  font-size: 24rpx;
  color: #b08093;
}
</style>
