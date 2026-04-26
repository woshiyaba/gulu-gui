<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { fetchLineupsByIds } from '@/api/pokemon'
import type { Lineup } from '@/types/banner'

const lineups = ref<Lineup[]>([])
const loading = ref(false)
const error = ref('')

const SOURCE_LABELS: Record<string, string> = {
  shining_contest: '闪耀大赛',
  open_battle: '露天对战',
  season_battle: '赛季对战',
  starlight_duel: '星光对决',
}

function sourceLabel(code: string): string {
  return SOURCE_LABELS[code] || code || '未分类'
}

function memberPreviewImages(lineup: Lineup): string[] {
  return lineup.members
    .slice(0, 6)
    .map((m) => m.pokemon_image)
    .filter(Boolean)
}

function navigateToDetail(id: number) {
  uni.navigateTo({ url: `/pages/lineup/detail?id=${id}` })
}

function goBattlePk() {
  uni.navigateTo({ url: '/pages/battle-pk/index' })
}

async function loadLineups(ids: number[]) {
  loading.value = true
  error.value = ''
  try {
    const resp = await fetchLineupsByIds(ids)
    lineups.value = resp.items || []
    if (lineups.value.length === 0) {
      error.value = '暂无阵容数据'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
}

onLoad((query) => {
  const raw = query?.ids || ''
  const ids = raw.split(',').map(Number).filter(Boolean)
  if (ids.length > 0) {
    void loadLineups(ids)
  } else {
    error.value = '缺少阵容参数'
  }
})
</script>

<template>
  <view class="page">
    <view v-if="loading" class="loading-box">
      <text class="loading-text">加载中...</text>
    </view>

    <view v-else-if="error" class="error-box">
      <text>{{ error }}</text>
    </view>

    <view v-if="!loading" class="pk-entry" @tap="goBattlePk">
      <view class="pk-entry-content">
        <text class="pk-entry-title">想 PK？模拟对战</text>
        <text class="pk-entry-desc">配置两套阵容，自动给胜率与回合推演</text>
      </view>
      <text class="pk-entry-arrow">›</text>
    </view>

    <view v-if="!loading && !error" class="lineup-grid">
      <view
        v-for="lineup in lineups"
        :key="lineup.id"
        class="lineup-card"
        @tap="navigateToDetail(lineup.id)"
      >
        <view class="card-header">
          <text class="source-tag">{{ sourceLabel(lineup.source_type) }}</text>
          <text class="lineup-title">{{ lineup.title || '阵容详情' }}</text>
        </view>

        <view v-if="lineup.resonance_magic_name" class="resonance-row">
          <image
            v-if="lineup.resonance_magic_icon"
            class="resonance-icon"
            :src="lineup.resonance_magic_icon"
            mode="aspectFit"
          />
          <text class="resonance-name">{{ lineup.resonance_magic_name }}</text>
        </view>

        <view class="pet-preview">
          <image
            v-for="(img, idx) in memberPreviewImages(lineup)"
            :key="idx"
            class="pet-avatar"
            :src="img"
            mode="aspectFit"
          />
          <view v-if="lineup.members.length > 6" class="pet-more">
            <text class="pet-more-text">+{{ lineup.members.length - 6 }}</text>
          </view>
        </view>

        <view class="card-footer">
          <text class="member-count">{{ lineup.members.length }}只精灵</text>
          <text class="tap-hint">点击查看详情 ›</text>
        </view>
      </view>
    </view>

    <view v-if="!loading && !error && lineups.length > 0" class="footer-status">
      <text class="footer-text">共 {{ lineups.length }} 套阵容</text>
    </view>
  </view>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 24rpx;
  background: linear-gradient(180deg, #f3f8ff 0%, #f9fbff 100%);
}

.loading-box {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400rpx;
}

.loading-text {
  font-size: 28rpx;
  color: #7a93bb;
}

.error-box {
  margin-bottom: 24rpx;
  padding: 24rpx 28rpx;
  border-radius: 28rpx;
  color: #c74646;
  background: #fff2f2;
  box-shadow: 0 12rpx 32rpx rgba(64, 125, 255, 0.08);
}

.pk-entry {
  display: flex; align-items: center; gap: 14rpx;
  margin-bottom: 24rpx; padding: 24rpx 28rpx;
  border-radius: 28rpx;
  background: linear-gradient(135deg, #2b74ff 0%, #f56c6c 100%);
  box-shadow: 0 12rpx 28rpx rgba(43, 116, 255, 0.22);
}
.pk-entry-content { flex: 1; min-width: 0; }
.pk-entry-title { display: block; font-size: 30rpx; font-weight: 700; color: #fff; }
.pk-entry-desc { display: block; margin-top: 4rpx; font-size: 22rpx; color: rgba(255,255,255,0.85); }
.pk-entry-arrow { font-size: 40rpx; color: rgba(255,255,255,0.85); }

.lineup-grid {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.lineup-card {
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 12rpx 32rpx rgba(64, 125, 255, 0.08);
  padding: 28rpx;
}

.card-header {
  margin-bottom: 16rpx;
}

.source-tag {
  display: inline-block;
  padding: 6rpx 18rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #2b74ff 0%, #53a0ff 100%);
  color: #ffffff;
  font-size: 22rpx;
  font-weight: 600;
}

.lineup-title {
  display: block;
  margin-top: 12rpx;
  font-size: 32rpx;
  font-weight: 700;
  color: #1f4ea3;
}

.resonance-row {
  display: flex;
  align-items: center;
  gap: 10rpx;
  margin-bottom: 14rpx;
}

.resonance-icon {
  width: 36rpx;
  height: 36rpx;
  border-radius: 6rpx;
}

.resonance-name {
  font-size: 24rpx;
  color: #5a81c9;
}

.pet-preview {
  display: flex;
  align-items: center;
  gap: 10rpx;
  margin-bottom: 14rpx;
  flex-wrap: wrap;
}

.pet-avatar {
  width: 80rpx;
  height: 80rpx;
  border-radius: 14rpx;
  background: linear-gradient(135deg, #e8f0ff 0%, #ffffff 100%);
}

.pet-more {
  width: 80rpx;
  height: 80rpx;
  border-radius: 14rpx;
  background: #eef4ff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pet-more-text {
  font-size: 22rpx;
  color: #7a93bb;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.member-count {
  font-size: 22rpx;
  color: #7a93bb;
}

.tap-hint {
  font-size: 22rpx;
  color: #2b74ff;
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
