<script setup lang="ts">
const props = defineProps<{
  groups: string[]
  selected: string[]
}>()

const emit = defineEmits<{
  (e: 'change', groups: string[]): void
}>()

function toggleGroup(group: string) {
  const selectedSet = new Set(props.selected)
  if (selectedSet.has(group)) {
    selectedSet.delete(group)
  } else {
    selectedSet.add(group)
  }
  emit('change', Array.from(selectedSet))
}
</script>

<template>
  <div class="egg-filter">
    <span class="egg-filter-label">蛋组</span>
    <button
      v-for="g in groups"
      :key="g"
      class="egg-btn"
      :class="{ active: selected.includes(g) }"
      @click="toggleGroup(g)"
    >
      {{ g }}
    </button>
  </div>
</template>

<style scoped>
.egg-filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 0 0 12px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 8px;
}

.egg-filter-label {
  font-size: 13px;
  color: var(--color-muted);
  margin-right: 4px;
}

.egg-btn {
  padding: 6px 12px;
  border: 2px solid transparent;
  border-radius: 16px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.egg-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.egg-btn.active {
  background: var(--color-accent);
  color: #fff;
  border-color: var(--color-accent);
}
</style>
