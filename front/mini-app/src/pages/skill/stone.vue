<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { fetchSkillStones } from '@/api/pokemon'
import type { SkillStone } from '@/types/pokemon'

const keyword = ref('')
const loading = ref(false)
const error = ref('')
const skillStones = ref<SkillStone[]>([])
const total = ref(0)
const hasLoaded = ref(false)

let searchTimer: ReturnType<typeof setTimeout> | undefined

const summaryText = computed(() => {
  if (!hasLoaded.value) return ''
  if (keyword.value.trim()) {
    return `关键词"${keyword.value.trim()}"共匹配到 ${total.value} 条技能石记录`
  }
  return `当前共收录 ${total.value} 条技能石记录`
})

async function loadSkillStones() {
  loading.value = true
  error.value = ''
  try {
    const skillName = keyword.value.trim()
    const res = await fetchSkillStones(skillName ? { skill_name: skillName } : {})
    skillStones.value = res.items
    total.value = res.total
    hasLoaded.value = true
  } catch {
    error.value = '查询失败，请稍后再试'
    skillStones.value = []
    total.value = 0
    hasLoaded.value = true
  } finally {
    loading.value = false
  }
}

function onSearchConfirm() {
  void loadSkillStones()
}

watch(keyword, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void loadSkillStones(), 300)
})

onLoad(() => {
  void loadSkillStones()
})
</script>

<template>
  <view class="page">
    <view class="search-card">
      <text class="page-title">技能石查询</text>
      <text class="page-subtitle">输入技能名关键词查询对应技能石获取方式。</text>
      <view class="search-box">
        <input
          v-model="keyword"
          class="search-input"
          confirm-type="search"
          placeholder="例如：光、龙、光合作用"
          @confirm="onSearchConfirm"
        />
      </view>
    </view>

    <view v-if="hasLoaded" class="summary-row">
      <text class="summary-text">{{ summaryText }}</text>
    </view>

    <view v-if="error" class="error-box">
      <text>{{ error }}</text>
    </view>

    <view v-if="loading && !hasLoaded" class="skeleton-grid">
      <view v-for="n in 6" :key="n" class="skeleton-card" />
    </view>

    <view v-else-if="skillStones.length === 0 && hasLoaded && !error" class="empty-box">
      <text class="empty-title">没有找到匹配的技能石</text>
      <text class="empty-tip">试试换个技能名关键词</text>
    </view>

    <view v-else class="stone-grid">
      <view v-for="item in skillStones" :key="item.skill_name" class="stone-card">
        <view class="stone-icon-wrap">
          <image v-if="item.icon" class="stone-icon" :src="item.icon" mode="aspectFit" />
          <view v-else class="stone-icon-placeholder">?</view>
        </view>
        <text class="stone-name">{{ item.skill_name }}</text>
        <text class="stone-method">{{ item.obtain_method }}</text>
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

.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
}

.skeleton-card {
  height: 240rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #edf4ff 0%, #ffffff 100%);
}

.stone-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
}

.stone-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12rpx;
  padding: 28rpx 20rpx;
  border-radius: 24rpx;
  background: #ffffff;
  box-shadow: 0 8rpx 24rpx rgba(64, 125, 255, 0.06);
}

.stone-icon-wrap {
  width: 96rpx;
  height: 96rpx;
  border-radius: 20rpx;
  background: #f3f8ff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stone-icon {
  width: 72rpx;
  height: 72rpx;
}

.stone-icon-placeholder {
  font-size: 36rpx;
  color: #b5c8e8;
}

.stone-name {
  font-size: 26rpx;
  font-weight: 700;
  color: #1f3760;
  text-align: center;
}

.stone-method {
  font-size: 22rpx;
  line-height: 1.7;
  color: #6f89b2;
  text-align: center;
  word-break: break-word;
}
</style>
