<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import type { Pokemon } from '@/types'

const props = defineProps<{ pokemon: Pokemon }>()
const router = useRouter()

const showYise = ref(false)

const displayImage = computed(() =>
  showYise.value && props.pokemon.image_yise_url
    ? props.pokemon.image_yise_url
    : props.pokemon.image_url
)

function toggleYise() {
  showYise.value = !showYise.value
}

function goDetail() {
  router.push(`/pokemon/${encodeURIComponent(props.pokemon.name)}`)
}
</script>

<template>
  <div class="pokemon-card" @click="goDetail">
    <div class="card-img-wrap">
      <img
        v-if="displayImage"
        :src="displayImage"
        :alt="pokemon.name"
        class="card-img"
        loading="lazy"
      />
      <div v-else class="card-img-placeholder">?</div>
    </div>

    <div class="card-body">
      <div class="card-no">{{ pokemon.no }}</div>
      <div class="card-name-row">
        <div class="card-name">{{ pokemon.name }}</div>
        <button
          v-if="pokemon.image_yise_url"
          class="yise-btn"
          :class="{ 'yise-btn--active': showYise }"
          @click.stop="toggleYise"
        >{{ showYise ? '普通' : '异色' }}</button>
      </div>

      <!-- 属性标签 -->
      <div class="card-attrs">
        <span
          v-for="a in pokemon.attributes"
          :key="a.attr_name"
          class="attr-tag"
        >
          <img v-if="a.attr_image" :src="a.attr_image" :alt="a.attr_name" class="attr-icon" />
          {{ a.attr_name }}
        </span>
      </div>

      <!-- 形态标签 -->
      <div class="card-meta">
        <span v-if="pokemon.type_name" class="meta-tag type-tag">{{ pokemon.type_name }}</span>
        <span v-if="pokemon.form_name" class="meta-tag form-tag">{{ pokemon.form_name }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pokemon-card {
  background: var(--color-surface);
  border-radius: 12px;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
  cursor: pointer;
  border: 1px solid var(--color-border);
}

.pokemon-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--color-shadow);
  border-color: var(--color-accent);
}

.card-img-wrap {
  background: var(--color-img-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  height: 140px;
}

.card-img {
  max-width: 100%;
  max-height: 130px;
  object-fit: contain;
}

.card-img-placeholder {
  font-size: 48px;
  color: var(--color-muted);
}

.card-body {
  padding: 10px 12px 12px;
}

.card-no {
  font-size: 11px;
  color: var(--color-muted);
  margin-bottom: 2px;
}

.card-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.card-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
}

.yise-btn {
  flex-shrink: 0;
  padding: 1px 8px;
  border: 1.5px solid var(--color-accent);
  border-radius: 10px;
  background: transparent;
  color: var(--color-accent);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.yise-btn:hover {
  background: var(--color-accent);
  color: #fff;
}

.yise-btn--active {
  background: var(--color-accent);
  color: #fff;
}

.card-attrs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 6px;
}

.attr-tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 8px;
  background: var(--color-tag-bg);
  border-radius: 10px;
  font-size: 11px;
  color: var(--color-text);
}

.attr-icon {
  width: 14px;
  height: 14px;
  object-fit: contain;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.meta-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 8px;
}

.type-tag {
  background: rgba(99, 102, 241, 0.15);
  color: #818cf8;
}

.form-tag {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
}
</style>
