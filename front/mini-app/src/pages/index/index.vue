<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { onLoad, onPullDownRefresh, onReachBottom, onUnload } from '@dcloudio/uni-app'
import PokemonCard from '@/components/PokemonCard.vue'
import { fetchAttributes, fetchPokemon, type PokemonQuery } from '@/api/pokemon'
import type { Attribute, Pokemon } from '@/types/pokemon'

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

function navigateToBodyMatch() {
  uni.navigateTo({
    url: '/pages/pokemon/body-match',
  })
}

async function initializePage() {
  await loadAttributes()
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
      <view class="hero-main">
        <view>
          <text class="hero-title">洛克王国精灵图鉴</text>
          <text class="hero-subtitle">支持按名称、属性快速查询，也可以根据身高体重找宠物。</text>
        </view>
        <button class="hero-button" @tap="navigateToBodyMatch">身高体重查宠</button>
      </view>

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

.hero-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20rpx;
}

.hero-title {
  display: block;
  font-size: 40rpx;
  font-weight: 700;
  color: #1f4ea3;
}

.hero-subtitle {
  display: block;
  margin-top: 10rpx;
  font-size: 24rpx;
  line-height: 1.6;
  color: #5f7da6;
}

.hero-button {
  margin: 0;
  padding: 0 26rpx;
  height: 72rpx;
  line-height: 72rpx;
  border: none;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #2b74ff 0%, #53a0ff 100%);
  color: #ffffff;
  font-size: 24rpx;
  font-weight: 600;
}

.hero-button::after {
  border: none;
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
