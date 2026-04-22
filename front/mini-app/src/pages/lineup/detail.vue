<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { fetchLineupDetail } from '@/api/pokemon'
import type { Lineup, LineupMember } from '@/types/banner'

const lineup = ref<Lineup | null>(null)
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

function getSkills(m: LineupMember) {
  const list: { name: string; image: string }[] = []
  if (m.skill_1_id) list.push({ name: m.skill_1_name, image: m.skill_1_image })
  if (m.skill_2_id) list.push({ name: m.skill_2_name, image: m.skill_2_image })
  if (m.skill_3_id) list.push({ name: m.skill_3_name, image: m.skill_3_image })
  if (m.skill_4_id) list.push({ name: m.skill_4_name, image: m.skill_4_image })
  return list
}

async function loadDetail(id: string) {
  loading.value = true
  error.value = ''
  try {
    lineup.value = await fetchLineupDetail(Number(id))
    if (!lineup.value) {
      error.value = '阵容不存在或未启用'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
}

onLoad((query) => {
  if (query?.id) {
    void loadDetail(query.id)
  } else {
    error.value = '缺少阵容ID'
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

    <template v-else-if="lineup">
      <view class="header-card">
        <text class="source-tag">{{ sourceLabel(lineup.source_type) }}</text>
        <text class="lineup-title">{{ lineup.title || '阵容详情' }}</text>
      </view>

      <view v-if="lineup.resonance_magic_name" class="section-card resonance-section">
        <view class="resonance-row">
          <image v-if="lineup.resonance_magic_icon" class="resonance-icon" :src="lineup.resonance_magic_icon" mode="aspectFit" />
          <text class="resonance-label">共鸣魔法</text>
          <text class="resonance-name">{{ lineup.resonance_magic_name }}</text>
        </view>
      </view>

      <view class="section-card">
        <text class="section-title">宠物阵容</text>
        <view class="pet-grid">
          <view v-for="m in lineup.members" :key="m.id" class="pet-card">
            <view class="pet-image-wrap">
              <image v-if="m.pokemon_image" class="pet-image" :src="m.pokemon_image" mode="aspectFit" />
              <view v-else class="pet-image-placeholder" />
            </view>
            <text class="pet-name">{{ m.pokemon_name }}</text>
            <view v-if="m.bloodline_label || m.personality_name_zh" class="tag-row">
              <text v-if="m.bloodline_label" class="tag bloodline-tag">{{ m.bloodline_label }}</text>
              <text v-if="m.personality_name_zh" class="tag personality-tag">{{ m.personality_name_zh }}</text>
            </view>
            <view class="skill-list">
              <view v-for="(sk, si) in getSkills(m)" :key="si" class="skill-item">
                <image v-if="sk.image" class="skill-icon" :src="sk.image" mode="aspectFit" />
                <text class="skill-tag">{{ sk.name }}</text>
              </view>
              <text v-if="getSkills(m).length === 0" class="skill-empty">任意技能</text>
            </view>
            <text v-if="m.member_desc" class="member-desc">{{ m.member_desc }}</text>
          </view>
        </view>
      </view>

      <view v-if="lineup.lineup_desc" class="section-card">
        <text class="section-title">打法说明</text>
        <text class="strategy-text">{{ lineup.lineup_desc }}</text>
      </view>
    </template>
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

.header-card,
.section-card {
  margin-bottom: 24rpx;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 12rpx 32rpx rgba(64, 125, 255, 0.08);
  padding: 28rpx;
}

.source-tag {
  display: inline-block;
  padding: 8rpx 20rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #2b74ff 0%, #53a0ff 100%);
  color: #ffffff;
  font-size: 24rpx;
  font-weight: 600;
}

.lineup-title {
  display: block;
  margin-top: 16rpx;
  font-size: 36rpx;
  font-weight: 700;
  color: #1f4ea3;
}

.resonance-section {
  padding: 20rpx 28rpx;
}

.resonance-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.resonance-icon {
  width: 44rpx;
  height: 44rpx;
  border-radius: 8rpx;
}

.resonance-label {
  font-size: 24rpx;
  color: #7a93bb;
}

.resonance-name {
  font-size: 28rpx;
  font-weight: 600;
  color: #1e3557;
}

.section-title {
  display: block;
  font-size: 30rpx;
  font-weight: 700;
  color: #214887;
  margin-bottom: 20rpx;
}

.pet-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16rpx;
}

.pet-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16rpx 8rpx;
  border-radius: 20rpx;
  background: #f5f9ff;
}

.pet-image-wrap {
  width: 140rpx;
  height: 140rpx;
  border-radius: 16rpx;
  overflow: hidden;
  background: linear-gradient(135deg, #e8f0ff 0%, #ffffff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.pet-image {
  width: 120rpx;
  height: 120rpx;
}

.pet-image-placeholder {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  background: #dbe6f5;
}

.pet-name {
  margin-top: 12rpx;
  font-size: 24rpx;
  font-weight: 600;
  color: #1e3557;
  text-align: center;
}

.tag-row {
  display: flex;
  gap: 6rpx;
  margin-top: 8rpx;
  flex-wrap: wrap;
  justify-content: center;
}

.tag {
  padding: 2rpx 12rpx;
  border-radius: 999rpx;
  font-size: 18rpx;
}

.bloodline-tag {
  background: rgba(245, 108, 108, 0.12);
  color: #f56c6c;
}

.personality-tag {
  background: rgba(103, 194, 58, 0.12);
  color: #67c23a;
}

.skill-list {
  margin-top: 10rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6rpx;
}

.skill-item {
  display: flex;
  align-items: center;
  gap: 6rpx;
}

.skill-icon {
  width: 28rpx;
  height: 28rpx;
  border-radius: 6rpx;
}

.skill-tag {
  padding: 4rpx 14rpx;
  border-radius: 999rpx;
  background: #e0ecff;
  color: #2b74ff;
  font-size: 20rpx;
  white-space: nowrap;
}

.skill-empty {
  font-size: 20rpx;
  color: #7a93bb;
}

.member-desc {
  margin-top: 8rpx;
  font-size: 20rpx;
  color: #7a93bb;
  text-align: center;
  line-height: 1.6;
}

.strategy-text {
  font-size: 28rpx;
  line-height: 1.8;
  color: #3a5a85;
  white-space: pre-wrap;
}
</style>
