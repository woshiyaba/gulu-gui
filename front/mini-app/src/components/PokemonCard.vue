<script setup lang="ts">
import type { Pokemon } from '@/types/pokemon'

defineProps<{
  pokemon: Pokemon
}>()

const emit = defineEmits<{
  select: [name: string]
}>()

function onTap(name: string) {
  emit('select', name)
}
</script>

<template>
  <view class="card" @tap="onTap(pokemon.name)">
    <view class="image-wrap">
      <image
        v-if="pokemon.image_url"
        class="pokemon-image"
        :src="pokemon.image_url"
        mode="aspectFit"
      />
      <view v-else class="image-placeholder">?</view>
    </view>

    <view class="meta">
      <text class="pokemon-no">#{{ pokemon.no || '--' }}</text>
      <text class="pokemon-name">{{ pokemon.name }}</text>

      <view class="tag-row">
        <text v-if="pokemon.type_name" class="meta-tag type-tag">{{ pokemon.type_name }}</text>
        <text v-if="pokemon.form_name" class="meta-tag form-tag">{{ pokemon.form_name }}</text>
      </view>

      <view class="attr-row">
        <view
          v-for="attr in pokemon.attributes"
          :key="attr.attr_name"
          class="attr-chip"
        >
          <image
            v-if="attr.attr_image"
            class="attr-icon"
            :src="attr.attr_image"
            mode="aspectFit"
          />
          <text class="attr-text">{{ attr.attr_name }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.card {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
  padding: 24rpx;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 10rpx 28rpx rgba(64, 125, 255, 0.08);
}

.image-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 220rpx;
  border-radius: 22rpx;
  background: linear-gradient(180deg, #edf5ff 0%, #f8fbff 100%);
}

.pokemon-image {
  width: 180rpx;
  height: 180rpx;
}

.image-placeholder {
  font-size: 72rpx;
  color: #b6c7e7;
}

.meta {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.pokemon-no {
  font-size: 22rpx;
  color: #89a0c7;
}

.pokemon-name {
  font-size: 32rpx;
  font-weight: 700;
  color: #1e3557;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}

.meta-tag {
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
}

.type-tag {
  color: #2761d8;
  background: rgba(39, 97, 216, 0.12);
}

.form-tag {
  color: #169b7b;
  background: rgba(22, 155, 123, 0.12);
}

.attr-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}

.attr-chip {
  display: inline-flex;
  align-items: center;
  gap: 6rpx;
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: #eff5ff;
}

.attr-icon {
  width: 26rpx;
  height: 26rpx;
}

.attr-text {
  font-size: 22rpx;
  color: #45638e;
}
</style>
