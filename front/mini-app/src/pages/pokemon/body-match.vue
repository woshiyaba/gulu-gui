<script setup lang="ts">
import { computed, ref } from 'vue'
import { fetchPokemonBodyMatch } from '@/api/pokemon'
import type { PokemonBodyMatchResponse } from '@/types/pokemon'

const heightInput = ref('')
const weightInput = ref('')
const loading = ref(false)
const error = ref('')
const result = ref<PokemonBodyMatchResponse | null>(null)

const hasSearched = computed(() => result.value !== null)

function parsePositiveNumber(raw: string) {
  const value = Number(raw)
  if (!Number.isFinite(value) || value <= 0) {
    return null
  }
  return value
}

function goBack() {
  if (getCurrentPages().length > 1) {
    uni.navigateBack()
    return
  }

  uni.reLaunch({
    url: '/pages/index/index',
  })
}

/** 量体结果项：用 pet_name 作为详情查询名（与图鉴列表的 name 参数区分） */
function openDetail(item: { pet_name: string }) {
  const petName = item.pet_name?.trim()
  if (!petName) return
  uni.navigateTo({
    url: `/pages/pokemon/detail?pet_name=${encodeURIComponent(petName)}`,
  })
}

async function onSubmit() {
  const heightM = parsePositiveNumber(heightInput.value)
  const weightKg = parsePositiveNumber(weightInput.value)

  if (heightM === null || weightKg === null) {
    error.value = '请输入大于 0 的身高（m）和体重（kg）。'
    result.value = null
    return
  }

  loading.value = true
  error.value = ''

  try {
    result.value = await fetchPokemonBodyMatch({
      height_m: heightM,
      weight_kg: weightKg,
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '查宠失败，请稍后再试'
    result.value = null
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <view class="page">
    <view class="top-actions">
      <button class="back-button" @tap="goBack">返回图鉴</button>
    </view>

    <view class="panel hero-panel">
      <text class="page-title">孵蛋查询</text>
      <text class="page-subtitle">输入身高和体重，系统会自动换算并匹配对应宠物。</text>
    </view>

    <view class="panel form-panel">
      <view class="field-group">
        <text class="field-label">身高（m）</text>
        <input
          v-model="heightInput"
          class="field-input"
          type="digit"
          placeholder="例如 0.27"
          @confirm="onSubmit"
        />
      </view>

      <view class="field-group">
        <text class="field-label">体重（kg）</text>
        <input
          v-model="weightInput"
          class="field-input"
          type="digit"
          placeholder="例如 1.36"
          @confirm="onSubmit"
        />
      </view>

      <button class="submit-button" :disabled="loading" @tap="onSubmit">
        {{ loading ? '查询中...' : '开始查询' }}
      </button>
    </view>

    <view v-if="error" class="error-panel">
      <text class="error-text">{{ error }}</text>
    </view>

    <view v-if="result" class="panel result-panel">
      <text class="section-title">查询结果</text>
      <text class="summary-text">
        输入 {{ result.height_m }} m / {{ result.weight_kg }} kg，
        已换算为 {{ result.height_cm }} cm / {{ result.weight_g }} g，
        共匹配到 {{ result.total }} 只宠物。
      </text>

      <view v-if="result.total === 0" class="empty-wrap">
        <text class="empty-text">没有找到符合这组条件的宠物</text>
      </view>

      <view v-else class="result-list">
        <view
          v-for="item in result.items"
          :key="item.pet_name"
          class="result-item"
          @tap="openDetail(item)"
        >
          <text class="result-name">{{ item.pet_name }}</text>
          <text class="result-link">查看详情</text>
        </view>
      </view>
    </view>

    <view v-else-if="!loading && !hasSearched" class="panel tips-panel">
      <text class="section-title">使用说明</text>
      <view class="tip-list">
        <text class="tip-item">1. 身高和体重都必须大于 0。</text>
        <text class="tip-item">2. 系统会把 m 转成 cm、kg 转成 g 后做区间匹配。</text>
        <text class="tip-item">3. 只有同时满足身高和体重条件的宠物才会返回。</text>
      </view>
    </view>
  </view>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 24rpx;
  background: linear-gradient(180deg, #f4f8ff 0%, #fafdff 100%);
}

.top-actions {
  margin-bottom: 20rpx;
}

.back-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  padding: 0 26rpx;
  height: 66rpx;
  line-height: 66rpx;
  border: 1rpx solid #7eaef8;
  border-radius: 999rpx;
  background: #ffffff;
  color: #2c66d2;
  font-size: 24rpx;
}

.back-button::after {
  border: none;
}

.panel,
.error-panel {
  margin-bottom: 24rpx;
  padding: 28rpx;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 12rpx 32rpx rgba(64, 125, 255, 0.08);
}

.page-title {
  display: block;
  font-size: 40rpx;
  font-weight: 700;
  color: #1f4ea3;
}

.page-subtitle,
.summary-text,
.tip-item {
  display: block;
  margin-top: 14rpx;
  font-size: 24rpx;
  line-height: 1.8;
  color: #6a84ac;
}

.form-panel {
  display: flex;
  flex-direction: column;
  gap: 22rpx;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.field-label,
.section-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #214887;
}

.field-input {
  height: 82rpx;
  padding: 0 24rpx;
  border-radius: 22rpx;
  background: #f4f8ff;
  font-size: 28rpx;
  color: #1f3760;
}

.submit-button {
  margin: 8rpx 0 0;
  height: 84rpx;
  line-height: 84rpx;
  border: none;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #2b74ff 0%, #53a0ff 100%);
  color: #ffffff;
  font-size: 28rpx;
  font-weight: 600;
}

.submit-button::after {
  border: none;
}

.submit-button[disabled] {
  opacity: 0.7;
}

.error-panel {
  background: #fff2f2;
}

.error-text {
  font-size: 28rpx;
  line-height: 1.7;
  color: #c74646;
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
  margin-top: 24rpx;
}

.result-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  padding: 24rpx;
  border-radius: 24rpx;
  background: #f8fbff;
}

.result-name {
  font-size: 28rpx;
  font-weight: 700;
  color: #1f3760;
}

.result-link {
  font-size: 22rpx;
  color: #2b74ff;
}

.empty-wrap {
  margin-top: 24rpx;
}

.empty-text {
  font-size: 26rpx;
  color: #6a84ac;
}

.tip-list {
  margin-top: 10rpx;
}
</style>
