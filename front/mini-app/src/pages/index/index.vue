<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { onLoad, onPullDownRefresh, onReachBottom, onUnload } from '@dcloudio/uni-app'
import PokemonCard from '@/components/PokemonCard.vue'
import {
  fetchAttributes,
  fetchBanners,
  fetchMerchantInfo,
  fetchPokemon,
  type MerchantInfo,
  type PokemonQuery,
} from '@/api/pokemon'
import type { Attribute, Pokemon } from '@/types/pokemon'
import type { Banner } from '@/types/banner'

const banners = ref<Banner[]>([])
const attributes = ref<Attribute[]>([])
const pokemons = ref<Pokemon[]>([])
const total = ref(0)
const loading = ref(false)
const loadingAttributes = ref(false)
const error = ref('')

const searchName = ref('')
const selectedAttr = ref('')
const currentPage = ref(1)
const pageSize = 30

const merchantInfo = ref<MerchantInfo | null>(null)
const merchantLoading = ref(false)
const merchantError = ref('')
const nowMs = ref(Date.now())

let searchTimer: ReturnType<typeof setTimeout> | undefined
let merchantTimer: ReturnType<typeof setInterval> | undefined
let merchantRefreshScheduled = false

const isInitialLoading = computed(() => loading.value && pokemons.value.length === 0)
const hasMore = computed(() => pokemons.value.length < total.value)

async function loadAttributes() {
  loadingAttributes.value = true
  try {
    attributes.value = await fetchAttributes()
  } catch {
    attributes.value = []
  } finally {
    loadingAttributes.value = false
  }
}

async function loadPokemon(reset = false) {
  if (loading.value) return

  if (reset) {
    currentPage.value = 1
    pokemons.value = []
    total.value = 0
  }

  loading.value = true
  error.value = ''

  try {
    // 仅在有筛选条件时带上 name/attr，首屏请求即为 /api/pokemon?page=1&page_size=30
    const query: PokemonQuery = {
      page: currentPage.value,
      page_size: pageSize,
    }
    const trimmedName = searchName.value.trim()
    if (trimmedName) query.name = trimmedName
    if (selectedAttr.value) query.attr = selectedAttr.value

    const response = await fetchPokemon(query)

    pokemons.value = reset
      ? response.items
      : [...pokemons.value, ...response.items]
    total.value = response.total
  } catch (err) {
    error.value = err instanceof Error ? err.message : '图鉴加载失败，请稍后再试'
  } finally {
    loading.value = false
    uni.stopPullDownRefresh()
  }
}

async function resetAndLoadPokemon() {
  await loadPokemon(true)
}

async function loadNextPage() {
  if (loading.value || !hasMore.value || !!error.value) return

  currentPage.value += 1
  await loadPokemon()

  if (error.value) {
    currentPage.value -= 1
  }
}

function toggleAttr(attrName: string) {
  selectedAttr.value = selectedAttr.value === attrName ? '' : attrName
}

function onSearchConfirm() {
  void resetAndLoadPokemon()
}

function navigateToDetail(name: string) {
  uni.navigateTo({
    url: `/pages/pokemon/detail?name=${encodeURIComponent(name)}`,
  })
}

const visibleMerchantProducts = computed(() => {
  const products = merchantInfo.value?.products ?? []
  return products.filter((p) => !p.end_time || p.end_time > nowMs.value)
})

function formatCountdown(endTime: number | null): string {
  if (!endTime) return '全天供应'
  const remaining = endTime - nowMs.value
  if (remaining <= 0) return '已结束'
  const totalSeconds = Math.floor(remaining / 1000)
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  const pad = (n: number) => String(n).padStart(2, '0')
  if (days > 0) return `${days}天 ${pad(hours)}:${pad(minutes)}:${pad(seconds)}`
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`
}

async function loadMerchant() {
  if (merchantLoading.value) return
  merchantLoading.value = true
  merchantError.value = ''
  try {
    merchantInfo.value = await fetchMerchantInfo()
    merchantRefreshScheduled = false
  } catch (err) {
    merchantError.value = err instanceof Error ? err.message : '远行商人加载失败'
  } finally {
    merchantLoading.value = false
  }
}

function startMerchantTimer() {
  stopMerchantTimer()
  merchantTimer = setInterval(() => {
    nowMs.value = Date.now()
    if (merchantRefreshScheduled) return
    const products = merchantInfo.value?.products ?? []
    const expired = products.some((p) => p.end_time && p.end_time <= nowMs.value)
    if (expired) {
      merchantRefreshScheduled = true
      void loadMerchant()
    }
  }, 1000)
}

function stopMerchantTimer() {
  if (merchantTimer) {
    clearInterval(merchantTimer)
    merchantTimer = undefined
  }
}

function refreshMerchant() {
  if (merchantLoading.value) return
  void loadMerchant()
}

function onBannerTap(index: number) {
  const banner = banners.value[index]
  if (!banner?.link_type || !banner.link_param) return
  if (banner.link_extra === 'multi') {
    uni.navigateTo({ url: `/pages/lineup/list?ids=${banner.link_param}` })
  } else {
    // single 模式：直接跳转阵容详情
    uni.navigateTo({ url: `/pages/lineup/detail?id=${banner.link_param}` })
  }
}

async function loadBanners() {
  try {
    banners.value = await fetchBanners()
  } catch {
    banners.value = []
  }
}

async function initializePage() {
  await Promise.all([loadBanners(), loadAttributes(), loadMerchant()])
  startMerchantTimer()
  await resetAndLoadPokemon()
}

watch(searchName, () => {
  if (searchTimer) {
    clearTimeout(searchTimer)
  }

  searchTimer = setTimeout(() => {
    void resetAndLoadPokemon()
  }, 300)
})

watch(selectedAttr, () => {
  void resetAndLoadPokemon()
})

onLoad(() => {
  void initializePage()
})

onReachBottom(() => {
  void loadNextPage()
})

onPullDownRefresh(() => {
  void resetAndLoadPokemon()
})

onUnload(() => {
  if (searchTimer) {
    clearTimeout(searchTimer)
  }
  stopMerchantTimer()
})
</script>

<template>
  <view class="page">
    <view class="hero-card">
      <swiper
        v-if="banners.length > 0"
        class="banner-swiper"
        :autoplay="true"
        :circular="true"
        :indicator-dots="banners.length > 1"
        indicator-color="rgba(255,255,255,0.4)"
        indicator-active-color="#ffffff"
        :interval="4000"
        :duration="500"
      >
        <swiper-item v-for="(banner, index) in banners" :key="banner.id" @tap="onBannerTap(index)">
          <image class="banner-image" :src="banner.image_url" mode="aspectFill" />
        </swiper-item>
      </swiper>

      <view class="search-box">
        <input
          v-model="searchName"
          class="search-input"
          confirm-type="search"
          placeholder="搜索宠物名称"
          @confirm="onSearchConfirm"
        />
      </view>

      <view class="summary-row">
        <text class="summary-text" v-if="total > 0">已展示 {{ pokemons.length }} / {{ total }} 只精灵</text>
        <text class="summary-text" v-else-if="loading">图鉴加载中...</text>
        <text class="summary-text" v-else>共 0 只精灵</text>
      </view>
    </view>

    <view class="merchant-card">
      <view class="merchant-head">
        <view class="merchant-head-text">
          <text class="merchant-title">{{ merchantInfo?.title || '远行商人' }}</text>
          <text v-if="merchantInfo?.subtitle" class="merchant-subtitle">{{ merchantInfo.subtitle }}</text>
        </view>
        <view
          class="merchant-refresh"
          :class="{ rotating: merchantLoading }"
          @tap="refreshMerchant"
        >
          <text class="merchant-refresh-icon">⟳</text>
        </view>
      </view>

      <view v-if="merchantError" class="merchant-status merchant-status-error">{{ merchantError }}</view>
      <view
        v-else-if="merchantLoading && visibleMerchantProducts.length === 0"
        class="merchant-status"
      >商品加载中...</view>
      <view
        v-else-if="visibleMerchantProducts.length === 0"
        class="merchant-status"
      >当前轮次暂无商品</view>
      <scroll-view v-else class="merchant-scroll" scroll-x>
        <view class="merchant-list">
          <view
            v-for="product in visibleMerchantProducts"
            :key="`${product.name}-${product.end_time ?? 'all'}`"
            class="merchant-item"
          >
            <view class="merchant-item-icon-wrap">
              <image
                v-if="product.icon_url"
                class="merchant-item-icon"
                :src="product.icon_url"
                mode="aspectFit"
              />
            </view>
            <text class="merchant-item-name">{{ product.name }}</text>
            <text class="merchant-item-countdown">{{ formatCountdown(product.end_time) }}</text>
          </view>
        </view>
      </scroll-view>
    </view>

    <view class="filter-card">
      <view class="section-head">
        <text class="section-title">属性筛选</text>
        <text class="section-tip" v-if="selectedAttr">当前：{{ selectedAttr }}</text>
      </view>

      <scroll-view class="attr-scroll" scroll-x>
        <view class="attr-list">
          <view
            class="attr-pill"
            :class="{ active: selectedAttr === '' }"
            @tap="toggleAttr('')"
          >
            全部
          </view>
          <view
            v-for="attr in attributes"
            :key="attr.attr_name"
            class="attr-pill"
            :class="{ active: selectedAttr === attr.attr_name }"
            @tap="toggleAttr(attr.attr_name)"
          >
            <image
              v-if="attr.attr_image"
              class="attr-pill-icon"
              :src="attr.attr_image"
              mode="aspectFit"
            />
            <text>{{ attr.attr_name }}</text>
          </view>
          <view v-if="loadingAttributes && attributes.length === 0" class="attr-loading">
            加载属性中...
          </view>
        </view>
      </scroll-view>
    </view>

    <view v-if="error" class="error-box">
      {{ error }}
    </view>

    <view v-if="isInitialLoading" class="skeleton-grid">
      <view v-for="item in 6" :key="item" class="skeleton-card" />
    </view>

    <view v-else-if="pokemons.length === 0 && !error" class="empty-box">
      <text class="empty-title">没有找到匹配的精灵</text>
      <text class="empty-tip">换个名称关键词，或者试试切换属性筛选。</text>
    </view>

    <view v-else class="pokemon-grid">
      <PokemonCard
        v-for="pokemon in pokemons"
        :key="pokemon.id"
        :pokemon="pokemon"
        @select="navigateToDetail"
      />
    </view>

    <view v-if="pokemons.length > 0 && !error" class="footer-status">
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
  padding-bottom: calc(40rpx + env(safe-area-inset-bottom));
  background: linear-gradient(180deg, #f3f8ff 0%, #f9fbff 100%);
}

.hero-card,
.filter-card,
.empty-box,
.error-box {
  margin-bottom: 24rpx;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 12rpx 32rpx rgba(64, 125, 255, 0.08);
}

.hero-card,
.filter-card {
  padding: 28rpx;
}

.merchant-card {
  margin-bottom: 20rpx;
  padding: 14rpx 18rpx 16rpx;
  border-radius: 20rpx;
  background: linear-gradient(135deg, #6f4dff 0%, #2b74ff 100%);
  box-shadow: 0 8rpx 20rpx rgba(43, 116, 255, 0.2);
}

.merchant-head {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 10rpx;
}

.merchant-head-text {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 12rpx;
}

.merchant-title {
  font-size: 26rpx;
  font-weight: 700;
  color: #ffffff;
}

.merchant-subtitle {
  font-size: 20rpx;
  color: rgba(255, 255, 255, 0.78);
}

.merchant-refresh {
  width: 40rpx;
  height: 40rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
}

.merchant-refresh-icon {
  font-size: 24rpx;
  color: #ffffff;
  line-height: 1;
}

.merchant-refresh.rotating .merchant-refresh-icon {
  animation: merchant-spin 0.9s linear infinite;
}

@keyframes merchant-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.merchant-status {
  padding: 12rpx 4rpx 4rpx;
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.78);
}

.merchant-status-error {
  color: #ffd6d6;
}

.merchant-scroll {
  white-space: nowrap;
}

.merchant-list {
  display: inline-flex;
  align-items: stretch;
  gap: 10rpx;
  padding: 2rpx 0;
}

.merchant-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4rpx;
  width: 116rpx;
  padding: 10rpx 8rpx;
  border-radius: 14rpx;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.06);
}

.merchant-item-icon-wrap {
  width: 64rpx;
  height: 64rpx;
  border-radius: 12rpx;
  background: #f3f6ff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.merchant-item-icon {
  width: 56rpx;
  height: 56rpx;
}

.merchant-item-name {
  font-size: 22rpx;
  font-weight: 600;
  color: #1f3460;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.merchant-item-countdown {
  font-size: 20rpx;
  color: #c14b4b;
  font-variant-numeric: tabular-nums;
}

.banner-swiper {
  height: 280rpx;
  border-radius: 20rpx;
  overflow: hidden;
  margin-bottom: 20rpx;
}

.banner-image {
  width: 100%;
  height: 100%;
  border-radius: 20rpx;
}

.search-box {
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

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 20rpx;
}

.section-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #214887;
}

.section-tip {
  font-size: 22rpx;
  color: #5a81c9;
}

.attr-scroll {
  white-space: nowrap;
}

.attr-list {
  display: inline-flex;
  align-items: center;
  gap: 16rpx;
  padding-bottom: 4rpx;
}

.attr-pill {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  padding: 14rpx 22rpx;
  border-radius: 999rpx;
  background: #eef4ff;
  color: #45638e;
  font-size: 24rpx;
  white-space: nowrap;
}

.attr-pill.active {
  background: linear-gradient(135deg, #2b74ff 0%, #53a0ff 100%);
  color: #ffffff;
}

.attr-pill-icon {
  width: 28rpx;
  height: 28rpx;
}

.attr-loading {
  font-size: 22rpx;
  color: #89a0c7;
}

.error-box {
  padding: 24rpx 28rpx;
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
  line-height: 1.7;
  color: #7a93bb;
  text-align: center;
}

.pokemon-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16rpx;
}

.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16rpx;
}

.skeleton-card {
  height: 280rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #edf4ff 0%, #ffffff 100%);
}

/* 376px 这类窄屏继续用 3 列会把卡片挤得太窄，标签换行后容易上下错位。 */
@media screen and (max-width: 390px) {
  .pokemon-grid,
  .skeleton-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 20rpx;
  }
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
