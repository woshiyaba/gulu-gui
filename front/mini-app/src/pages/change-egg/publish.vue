<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { createListing, fetchEggTags, type ChangeEggTag } from '@/api/changeEgg'
import { fetchPokemon } from '@/api/pokemon'
import type { Pokemon } from '@/types/pokemon'
import { getStoredUserId } from '@/utils/auth'

interface PickedPokemon {
  id: number
  name: string
  avatar: string
}

const userId = ref(getStoredUserId())
const gameId = ref('')
const ownPokemon = ref<PickedPokemon | null>(null)
const wantPokemon = ref<PickedPokemon | null>(null)
const ownTag = ref('')
const wantTag = ref('')
const tags = ref<ChangeEggTag[]>([])
const submitting = ref(false)

// 精灵选择弹窗
const pickerVisible = ref(false)
const pickerTarget = ref<'own' | 'want'>('own')
const keyword = ref('')
const results = ref<Pokemon[]>([])
const searching = ref(false)
let searchTimer: ReturnType<typeof setTimeout> | undefined

const canSubmit = computed(
  () =>
    !!userId.value &&
    gameId.value.trim().length > 0 &&
    !!ownPokemon.value &&
    !!wantPokemon.value &&
    (tags.value.length === 0 || (!!ownTag.value && !!wantTag.value)) &&
    !submitting.value,
)

onLoad(async () => {
  userId.value = getStoredUserId()
  try {
    tags.value = await fetchEggTags()
  } catch {
    tags.value = []
  }
})

function openPicker(target: 'own' | 'want') {
  pickerTarget.value = target
  keyword.value = ''
  results.value = []
  pickerVisible.value = true
}

function closePicker() {
  pickerVisible.value = false
}

async function runSearch() {
  const name = keyword.value.trim()
  if (!name) {
    results.value = []
    return
  }
  searching.value = true
  try {
    const res = await fetchPokemon({ name, page: 1, page_size: 20 })
    results.value = res.items
  } catch {
    results.value = []
  } finally {
    searching.value = false
  }
}

watch(keyword, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void runSearch(), 300)
})

function pickPokemon(item: Pokemon) {
  const picked: PickedPokemon = { id: item.id, name: item.name, avatar: item.image_url }
  if (pickerTarget.value === 'own') ownPokemon.value = picked
  else wantPokemon.value = picked
  closePicker()
}

function selectOwnTag(code: string) {
  ownTag.value = ownTag.value === code ? '' : code
}
function selectWantTag(code: string) {
  wantTag.value = wantTag.value === code ? '' : code
}

async function handleSubmit() {
  if (!userId.value) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    return
  }
  if (!canSubmit.value) {
    uni.showToast({ title: '请完整填写信息', icon: 'none' })
    return
  }
  submitting.value = true
  try {
    await createListing({
      user_id: userId.value,
      game_id: gameId.value.trim(),
      own_pokemon_id: ownPokemon.value!.id,
      own_tag: ownTag.value,
      want_pokemon_id: wantPokemon.value!.id,
      want_tag: wantTag.value,
    })
    uni.showToast({ title: '发布成功', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 900)
  } catch (err) {
    uni.showToast({ title: err instanceof Error ? err.message : '发布失败', icon: 'none' })
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <view class="page">
    <view class="hero-card">
      <text class="hero-title">发布换蛋</text>
      <text class="hero-subtitle">填写拥有 / 想要的精灵蛋组，立即开始匹配。</text>
    </view>

    <view class="form-card">
      <text class="label">我的游戏 ID</text>
      <input
        v-model="gameId"
        class="text-input"
        placeholder="请输入游戏内 ID（长串数字）"
        :maxlength="64"
      />

      <text class="label">我拥有的精灵蛋组</text>
      <view class="picker-row" @tap="openPicker('own')">
        <image v-if="ownPokemon" class="picker-avatar" :src="ownPokemon.avatar" mode="aspectFit" />
        <view v-else class="picker-avatar placeholder">+</view>
        <text class="picker-name">{{ ownPokemon ? ownPokemon.name : '点击选择精灵' }}</text>
        <text class="picker-arrow">›</text>
      </view>
      <view v-if="tags.length" class="tag-list">
        <view
          v-for="t in tags"
          :key="t.code"
          class="tag-chip"
          :class="{ active: ownTag === t.code }"
          @tap="selectOwnTag(t.code)"
        >
          <text class="tag-text">{{ t.label }}</text>
        </view>
      </view>

      <text class="label">我想要的精灵蛋组</text>
      <view class="picker-row" @tap="openPicker('want')">
        <image v-if="wantPokemon" class="picker-avatar" :src="wantPokemon.avatar" mode="aspectFit" />
        <view v-else class="picker-avatar placeholder">+</view>
        <text class="picker-name">{{ wantPokemon ? wantPokemon.name : '点击选择精灵' }}</text>
        <text class="picker-arrow">›</text>
      </view>
      <view v-if="tags.length" class="tag-list">
        <view
          v-for="t in tags"
          :key="t.code"
          class="tag-chip"
          :class="{ active: wantTag === t.code }"
          @tap="selectWantTag(t.code)"
        >
          <text class="tag-text">{{ t.label }}</text>
        </view>
      </view>
    </view>

    <button class="submit-btn" :disabled="!canSubmit" :loading="submitting" @tap="handleSubmit">
      发布并开始匹配
    </button>

    <!-- 精灵选择弹窗 -->
    <view v-if="pickerVisible" class="picker-mask" @tap="closePicker">
      <view class="picker-panel" @tap.stop>
        <view class="picker-header">
          <text class="picker-title">选择精灵</text>
          <text class="picker-close" @tap="closePicker">✕</text>
        </view>
        <input
          v-model="keyword"
          class="picker-search"
          confirm-type="search"
          placeholder="输入精灵名称搜索"
          focus
        />
        <scroll-view scroll-y class="picker-results">
          <view v-if="searching" class="picker-tip">搜索中...</view>
          <view v-else-if="keyword.trim() && results.length === 0" class="picker-tip">未找到匹配的精灵</view>
          <view
            v-for="item in results"
            :key="item.id"
            class="result-item"
            @tap="pickPokemon(item)"
          >
            <image class="result-avatar" :src="item.image_url" mode="aspectFit" />
            <view class="result-info">
              <text class="result-name">{{ item.name }}</text>
              <text class="result-no">{{ item.no }}</text>
            </view>
          </view>
        </scroll-view>
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
  margin-bottom: 24rpx;
  padding: 36rpx 28rpx;
  border-radius: 28rpx;
  background: linear-gradient(135deg, #9c5bff 0%, #53a0ff 100%);
  box-shadow: 0 12rpx 32rpx rgba(108, 99, 255, 0.22);
}
.hero-title { display: block; font-size: 40rpx; font-weight: 700; color: #ffffff; }
.hero-subtitle {
  display: block;
  margin-top: 10rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.85);
}

.form-card {
  padding: 28rpx;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 8rpx 24rpx rgba(64, 125, 255, 0.06);
}

.label {
  display: block;
  margin: 24rpx 0 14rpx;
  font-size: 28rpx;
  font-weight: 700;
  color: #214887;
}
.label:first-child { margin-top: 0; }

.text-input {
  width: 100%;
  height: 80rpx;
  padding: 0 20rpx;
  box-sizing: border-box;
  border-radius: 16rpx;
  background: #f7faff;
  font-size: 28rpx;
  color: #1f3760;
}

.picker-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 16rpx 20rpx;
  border-radius: 16rpx;
  background: #f7faff;
}
.picker-avatar {
  width: 72rpx;
  height: 72rpx;
  border-radius: 14rpx;
  background: linear-gradient(180deg, #edf5ff 0%, #f8fbff 100%);
}
.picker-avatar.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40rpx;
  color: #b6c7e7;
}
.picker-name { flex: 1; min-width: 0; font-size: 28rpx; color: #1f3760; }
.picker-arrow { font-size: 36rpx; color: #b5c8e8; }

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
  margin-top: 16rpx;
}
.tag-chip {
  padding: 12rpx 28rpx;
  border-radius: 999rpx;
  background: #f0f5ff;
  border: 2rpx solid transparent;
}
.tag-chip.active { background: #fff4e4; border-color: #f08b3a; }
.tag-text { font-size: 26rpx; color: #5a76a8; }
.tag-chip.active .tag-text { color: #f08b3a; font-weight: 700; }

.submit-btn {
  margin-top: 32rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #9c5bff 0%, #53a0ff 100%);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 700;
  box-shadow: 0 12rpx 28rpx rgba(108, 99, 255, 0.22);
}
.submit-btn[disabled] { opacity: 0.5; box-shadow: none; }

.picker-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 30, 60, 0.45);
  display: flex;
  align-items: flex-end;
  z-index: 50;
}
/* 固定高度 + 内部滚动：弹窗框架上下固定，搜索结果数量变化时只在内部向下滚动，
   不让整个面板随结果增减而上下浮动跳动。 */
.picker-panel {
  width: 100%;
  height: 80vh;
  display: flex;
  flex-direction: column;
  padding: 28rpx;
  box-sizing: border-box;
  border-radius: 28rpx 28rpx 0 0;
  background: #ffffff;
}
.picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18rpx;
  flex-shrink: 0;
}
.picker-title { font-size: 32rpx; font-weight: 700; color: #1f3760; }
.picker-close { font-size: 32rpx; color: #9fb1cf; }
.picker-search {
  width: 100%;
  height: 78rpx;
  padding: 0 24rpx;
  box-sizing: border-box;
  border-radius: 999rpx;
  background: #f3f8ff;
  font-size: 28rpx;
  color: #1f3760;
  flex-shrink: 0;
}
.picker-results { flex: 1; min-height: 0; margin-top: 18rpx; }
.picker-tip { padding: 40rpx; text-align: center; font-size: 26rpx; color: #7a93bb; }
.result-item {
  display: flex;
  align-items: center;
  gap: 18rpx;
  padding: 16rpx 8rpx;
  border-bottom: 2rpx solid #f0f4fb;
}
.result-avatar {
  width: 72rpx;
  height: 72rpx;
  border-radius: 14rpx;
  background: #f3f8ff;
}
.result-info { flex: 1; min-width: 0; }
.result-name { display: block; font-size: 28rpx; font-weight: 700; color: #1f3760; }
.result-no { display: block; margin-top: 4rpx; font-size: 22rpx; color: #7a93bb; }
</style>
