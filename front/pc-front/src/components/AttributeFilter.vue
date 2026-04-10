<script setup lang="ts">
import type { Attribute } from '@/types'

const props = defineProps<{
  attributes: Attribute[]
  selected: string
}>()

const emit = defineEmits<{
  (e: 'change', attr: string): void
}>()
</script>

<template>
  <div class="attr-filter">
    <button
      class="attr-btn"
      :class="{ active: selected === '' }"
      @click="emit('change', '')"
    >
      全部
    </button>
    <button
      v-for="a in attributes"
      :key="a.attr_name"
      class="attr-btn"
      :class="{ active: selected === a.attr_name }"
      @click="emit('change', a.attr_name)"
    >
      <img v-if="a.attr_image" :src="a.attr_image" :alt="a.attr_name" class="attr-icon" />
      {{ a.attr_name }}
    </button>
  </div>
</template>

<style scoped>
.attr-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 0;
}

.attr-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  border: 2px solid transparent;
  border-radius: 20px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.attr-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.attr-btn.active {
  background: var(--color-accent);
  color: #fff;
  border-color: var(--color-accent);
}

.attr-icon {
  width: 18px;
  height: 18px;
  object-fit: contain;
}
</style>
