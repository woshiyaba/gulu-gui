<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import PokemonAlbum from '@/components/PokemonAlbum.vue'

const petId = ref(0)
const petName = ref('')
const error = ref('')

function goBack() {
  if (getCurrentPages().length > 1) {
    uni.navigateBack()
    return
  }
  uni.reLaunch({ url: '/pages/index/index' })
}

onLoad((options) => {
  const rawId = typeof options?.pet_id === 'string' ? options.pet_id : ''
  const rawName = typeof options?.name === 'string' ? options.name : ''
  petId.value = Number(rawId) || 0
  petName.value = decodeURIComponent(rawName)

  if (!petId.value) {
    error.value = '缺少宠物信息，暂时无法加载相册。'
    return
  }

  if (petName.value) {
    uni.setNavigationBarTitle({ title: `${petName.value} · 相册` })
  }
})
</script>

<template>
  <view class="page">
    <view class="top-actions">
      <button class="back-button" @tap="goBack">返回详情</button>
    </view>

    <view v-if="error" class="error-card">
      <text class="error-text">{{ error }}</text>
    </view>

    <PokemonAlbum
      v-else
      :pet-id="petId"
      :pet-name="petName"
      :active="true"
    />
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

.error-card {
  padding: 28rpx;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 12rpx 32rpx rgba(64, 125, 255, 0.08);
  text-align: center;
}

.error-text {
  font-size: 28rpx;
  line-height: 1.7;
  color: #c74646;
}
</style>
