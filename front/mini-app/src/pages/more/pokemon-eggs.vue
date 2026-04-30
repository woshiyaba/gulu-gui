<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { onLoad, onPullDownRefresh, onReachBottom, onUnload } from '@dcloudio/uni-app'
import { fetchPokemonEggs } from '@/api/pokemon'
import type { PokemonEgg } from '@/types/pokemon'

const keyword = ref('')
const eggs = ref<PokemonEgg[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 30
const loading = ref(false)
const error = ref('')
const hasLoaded = ref(false)

let searchTimer: ReturnType<typeof setTimeout> | undefined

const isInitialLoading = computed(() => loading.value && eggs.value.length === 0)
const hasMore = computed(() => eggs.value.length < total.value)

// 瀑布流：按索引取模切四列
const COLUMN_COUNT = 4
const columns = computed(() => {
  const cols: PokemonEgg[][] = Array.from({ length: COLUMN_COUNT }, () => [])
  eggs.value.forEach((item, index) => {
    cols[index % COLUMN_COUNT].push(item)
  })
  return cols
})

async function loadEggs(reset = false) {
  if (loading.value) return

  if (reset) {
    currentPage.value = 1
    eggs.value = []
    total.value = 0
  }

  loading.value = true
  error.value = ''

  try {
    const response = await fetchPokemonEggs({
      name: keyword.value.trim() || undefined,
      page: currentPage.value,
      page_size: pageSize,
    })

    eggs.value = reset ? response.items : [...eggs.value, ...response.items]
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
  await loadEggs(true)
}

async function loadNextPage() {
  if (loading.value || !hasMore.value || !!error.value) return

  currentPage.value += 1
  await loadEggs()

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

function goPokemonDetail(item: PokemonEgg) {
  const name = item.pokemon_name?.trim()
  if (!name) {
    uni.showToast({ title: '该精灵蛋暂未关联宠物', icon: 'none' })
    return
  }
  uni.navigateTo({
    url: `/pages/pokemon/detail?name=${encodeURIComponent(name)}`,
  })
}
</script>

<template>
  <view class="page">
    <view class="search-card">
      <text class="page-title">精灵蛋查询</text>
      <text class="page-subtitle">查看精灵蛋图鉴，按名称筛选你想要的孵化目标。</text>
      <view class="search-box">
        <input
          v-model="keyword"
          class="search-input"
          confirm-type="search"
          placeholder="按名称搜索，例如：火焰、水之"
        />
      </view>
      <view v-if="hasLoaded" class="summary-row">
        <text class="summary-text" v-if="total > 0">
          已展示 {{ eggs.length }} / {{ total }} 个精灵蛋
        </text>
        <text class="summary-text" v-else>未匹配到精灵蛋</text>
      </view>
    </view>

    <view v-if="error" class="error-box">
      <text>{{ error }}</text>
    </view>

    <view v-if="isInitialLoading" class="skeleton-grid">
      <view v-for="n in 6" :key="n" class="skeleton-card" />
    </view>

    <view v-else-if="eggs.length === 0 && hasLoaded && !error" class="empty-box">
      <text class="empty-title">没有找到匹配的精灵蛋</text>
      <text class="empty-tip">试试换个关键词</text>
    </view>

    <view v-else class="waterfall">
      <view
        v-for="(col, colIndex) in columns"
        :key="colIndex"
        class="waterfall-col"
      >
        <view
          v-for="item in col"
          :key="item.id"
          class="egg-card"
          :class="{ 'egg-card--clickable': !!item.pokemon_name }"
          @tap="goPokemonDetail(item)"
        >
          <view class="icon-wrap">
            <image
              v-if="item.icon"
              class="egg-icon"
              :src="item.icon"
              mode="aspectFit"
              lazy-load
            />
            <view v-else class="icon-placeholder">?</view>
          </view>
          <text class="egg-name">{{ item.name || '未命名' }}</text>
          <text class="egg-form">{{ item.form || '' }}</text>
        </view>
      </view>
    </view>

    <view v-if="eggs.length > 0 && !error" class="footer-status">
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
  margin-top: 18rpx;
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

.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10rpx;
}

.skeleton-card {
  height: 180rpx;
  border-radius: 18rpx;
  background: linear-gradient(135deg, #edf4ff 0%, #ffffff 100%);
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

.egg-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6rpx;
  height: 224rpx;
  padding: 12rpx 8rpx;
  box-sizing: border-box;
  border-radius: 18rpx;
  background: #ffffff;
  box-shadow: 0 8rpx 20rpx rgba(64, 125, 255, 0.08);
}

.egg-card--clickable {
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.egg-card--clickable:active {
  transform: scale(0.96);
  box-shadow: 0 4rpx 12rpx rgba(64, 125, 255, 0.18);
}

.icon-wrap {
  width: 100%;
  height: 110rpx;
  border-radius: 14rpx;
  background: linear-gradient(180deg, #edf5ff 0%, #f8fbff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.egg-icon {
  width: 90rpx;
  height: 90rpx;
}

.icon-placeholder {
  font-size: 38rpx;
  color: #b6c7e7;
}

.egg-name {
  width: 100%;
  height: 58rpx;
  font-size: 22rpx;
  font-weight: 700;
  color: #1f3760;
  text-align: center;
  line-height: 1.3;
  word-break: break-word;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.egg-form {
  display: block;
  width: 100%;
  height: 24rpx;
  font-size: 18rpx;
  line-height: 24rpx;
  color: #6f89b2;
  text-align: center;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.footer-status {
  display: flex;
  justify-content: center;
  padding: 28rpx 0 16rpx;
}

.footer-text {
  font-size: 24rpx;
  color: #7a93bb;
}
</style>
