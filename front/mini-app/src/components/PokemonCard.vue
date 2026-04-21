<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Pokemon } from '@/types/pokemon'

const props = defineProps<{
  pokemon: Pokemon
}>()

const emit = defineEmits<{
  select: [name: string]
}>()

const showYise = ref(false)

const displayImage = computed(() =>
  showYise.value && props.pokemon.image_yise_url
    ? props.pokemon.image_yise_url
    : props.pokemon.image_url
)

function toggleYise() {
  showYise.value = !showYise.value
}

function onTap(name: string) {
  emit('select', name)
}
</script>

<template>
  <view class="card" @tap="onTap(pokemon.name)">
    <view class="image-wrap">
      <image
        v-if="displayImage"
        class="pokemon-image"
        :src="displayImage"
        mode="aspectFit"
        lazy-load
      />
      <view v-else class="image-placeholder">?</view>
    </view>

    <view class="meta">
      <text class="pokemon-no">#{{ pokemon.no || '--' }}</text>
      <view class="name-row">
        <text class="pokemon-name">{{ pokemon.name }}</text>
        <text
          v-if="pokemon.image_yise_url"
          class="yise-btn"
          :class="{ 'yise-btn--active': showYise }"
          @tap.stop="toggleYise"
        >{{ showYise ? '普通' : '异色' }}</text>
      </view>

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
  gap: 12rpx;
  padding: 18rpx;
  border-radius: 24rpx;
  background: #ffffff;
  box-shadow: 0 10rpx 28rpx rgba(64, 125, 255, 0.08);
}

.image-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 148rpx;
  border-radius: 18rpx;
  background: linear-gradient(180deg, #edf5ff 0%, #f8fbff 100%);
}

.pokemon-image {
  width: 116rpx;
  height: 116rpx;
}

.image-placeholder {
  font-size: 54rpx;
  color: #b6c7e7;
}

.meta {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.pokemon-no {
  font-size: 18rpx;
  color: #89a0c7;
}

.name-row {
  display: flex;
  align-items: flex-start;
  gap: 6rpx;
}

.pokemon-name {
  display: -webkit-box;
  overflow: hidden;
  font-size: 24rpx;
  line-height: 1.4;
  font-weight: 700;
  color: #1e3557;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  min-height: 68rpx;
  flex: 1;
}

.yise-btn {
  flex-shrink: 0;
  padding: 2rpx 10rpx;
  border: 1px solid #2b74ff;
  border-radius: 999rpx;
  font-size: 18rpx;
  color: #2b74ff;
  background: transparent;
  white-space: nowrap;
  line-height: 1.6;
}

.yise-btn--active {
  background: #2b74ff;
  color: #ffffff;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6rpx;
}

.meta-tag {
  padding: 4rpx 10rpx;
  border-radius: 999rpx;
  font-size: 18rpx;
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
  gap: 6rpx;
}

.attr-chip {
  display: inline-flex;
  align-items: center;
  gap: 4rpx;
  padding: 4rpx 10rpx;
  border-radius: 999rpx;
  background: #eff5ff;
  max-width: 100%;
}

.attr-icon {
  width: 20rpx;
  height: 20rpx;
}

.attr-text {
  font-size: 18rpx;
  color: #45638e;
}
</style>
