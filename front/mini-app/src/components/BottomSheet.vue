<script setup lang="ts">
defineProps<{
  visible: boolean
  title?: string
}>()

const emit = defineEmits<{ close: [] }>()

function close() {
  emit('close')
}
</script>

<template>
  <view v-if="visible" class="sheet-mask" @tap="close">
    <view class="sheet" @tap.stop>
      <view class="sheet-head">
        <text class="sheet-title">{{ title }}</text>
        <text class="sheet-close" @tap="close">✕</text>
      </view>
      <view class="sheet-body">
        <slot />
      </view>
    </view>
  </view>
</template>

<style scoped>
.sheet-mask {
  position: fixed;
  inset: 0;
  z-index: 999;
  background: rgba(20, 40, 80, 0.45);
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.sheet {
  max-height: 78vh;
  display: flex;
  flex-direction: column;
  border-radius: 28rpx 28rpx 0 0;
  background: #ffffff;
  box-shadow: 0 -8rpx 32rpx rgba(31, 71, 163, 0.18);
}

.sheet-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28rpx 28rpx 16rpx;
  flex-shrink: 0;
}

.sheet-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #1f3760;
}

.sheet-close {
  width: 56rpx;
  height: 56rpx;
  text-align: center;
  line-height: 56rpx;
  font-size: 30rpx;
  color: #8aa2c9;
  border-radius: 50%;
  background: #f3f8ff;
}

.sheet-body {
  flex: 1;
  min-height: 0;
  padding: 0 28rpx 32rpx;
  display: flex;
  flex-direction: column;
}
</style>
