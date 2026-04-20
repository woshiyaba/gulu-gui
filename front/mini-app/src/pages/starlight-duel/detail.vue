<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { fetchStarlightDuelEpisode, fetchStarlightDuelLatest } from '@/api/pokemon'
import type { StarlightDuelEpisode } from '@/types/banner'

const episode = ref<StarlightDuelEpisode | null>(null)
const loading = ref(false)
const error = ref('')

async function loadEpisode(episodeNumber?: string) {
  loading.value = true
  error.value = ''
  try {
    if (episodeNumber) {
      episode.value = await fetchStarlightDuelEpisode(Number(episodeNumber))
    } else {
      episode.value = await fetchStarlightDuelLatest()
    }
    if (!episode.value) {
      error.value = '暂无星光对决攻略'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
}

function getSkills(pet: { skill_1_name: string; skill_2_name: string; skill_3_name: string; skill_4_name: string }) {
  return [pet.skill_1_name, pet.skill_2_name, pet.skill_3_name, pet.skill_4_name].filter(Boolean)
}

onLoad((query) => {
  void loadEpisode(query?.episode)
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

    <template v-else-if="episode">
      <view class="header-card">
        <text class="episode-tag">第 {{ episode.episode_number }} 期</text>
        <text class="episode-title">{{ episode.title || '星光对决' }}</text>
      </view>

      <view class="section-card">
        <text class="section-title">宠物阵容</text>
        <view class="pet-grid">
          <view v-for="pet in episode.pets" :key="pet.id" class="pet-card">
            <view class="pet-image-wrap">
              <image v-if="pet.pet_image" class="pet-image" :src="pet.pet_image" mode="aspectFit" />
              <view v-else class="pet-image-placeholder" />
            </view>
            <text class="pet-name">{{ pet.pet_name }}</text>
            <view class="skill-list">
              <text
                v-for="(skill, si) in getSkills(pet)"
                :key="si"
                class="skill-tag"
              >
                {{ skill }}
              </text>
              <text v-if="getSkills(pet).length === 0" class="skill-empty">任意技能</text>
            </view>
          </view>
        </view>
      </view>

      <view v-if="episode.strategy_text" class="section-card">
        <text class="section-title">打法说明</text>
        <text class="strategy-text">{{ episode.strategy_text }}</text>
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

.episode-tag {
  display: inline-block;
  padding: 8rpx 20rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #2b74ff 0%, #53a0ff 100%);
  color: #ffffff;
  font-size: 24rpx;
  font-weight: 600;
}

.episode-title {
  display: block;
  margin-top: 16rpx;
  font-size: 36rpx;
  font-weight: 700;
  color: #1f4ea3;
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

.skill-list {
  margin-top: 10rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6rpx;
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

.strategy-text {
  font-size: 28rpx;
  line-height: 1.8;
  color: #3a5a85;
  white-space: pre-wrap;
}
</style>
