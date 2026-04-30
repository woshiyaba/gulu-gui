<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { onLoad, onPullDownRefresh, onReachBottom, onUnload } from '@dcloudio/uni-app'
import PokemonCard from '@/components/PokemonCard.vue'
import { fetchAttributes, fetchBanners, fetchPokemon, type PokemonQuery } from '@/api/pokemon'
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

let searchTimer: ReturnType<typeof setTimeout> | undefined

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

function goBattlePk() {
  uni.navigateTo({ url: '/pages/battle-pk/index' })
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
  await Promise.all([loadBanners(), loadAttributes()])
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

    <view class="pk-banner" @tap="goBattlePk">
      <view class="pk-banner-content">
        <text class="pk-banner-title">阵容 PK · 模拟对战</text>
        <text class="pk-banner-desc">配两套队伍，一键看胜率与回合推演</text>
      </view>
      <text class="pk-banner-arrow">›</text>
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
        :key="pokemon.no || pokemon.name"
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

.pk-banner {
  display: flex;
  align-items: center;
  gap: 14rpx;
  margin-bottom: 24rpx;
  padding: 22rpx 26rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #2b74ff 0%, #f56c6c 100%);
  box-shadow: 0 12rpx 28rpx rgba(43, 116, 255, 0.22);
}
.pk-banner-content { flex: 1; min-width: 0; }
.pk-banner-title { display: block; font-size: 30rpx; font-weight: 700; color: #fff; }
.pk-banner-desc { display: block; margin-top: 4rpx; font-size: 22rpx; color: rgba(255,255,255,0.85); }
.pk-banner-arrow { font-size: 40rpx; color: rgba(255,255,255,0.85); }

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
