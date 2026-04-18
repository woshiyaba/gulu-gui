<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { fetchAttributes, fetchSkills, fetchSkillTypes, type SkillQuery } from '@/api/pokemon'
import type { Attribute, Skill } from '@/types/pokemon'

const attributes = ref<Attribute[]>([])
const skillTypes = ref<string[]>([])
const skills = ref<Skill[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const hasLoaded = ref(false)

const keyword = ref('')
const selectedType = ref('')
const selectedAttr = ref('')

let searchTimer: ReturnType<typeof setTimeout> | undefined

const typePickerRange = computed(() => ['全部类型', ...skillTypes.value])
const typePickerIndex = computed(() => {
  if (!selectedType.value) return 0
  const idx = skillTypes.value.indexOf(selectedType.value)
  return idx >= 0 ? idx + 1 : 0
})

const summaryText = computed(() => {
  if (!hasLoaded.value) return ''
  const parts: string[] = []
  if (keyword.value.trim()) parts.push(`名称"${keyword.value.trim()}"`)
  if (selectedType.value) parts.push(`类型"${selectedType.value}"`)
  if (selectedAttr.value) parts.push(`属性"${selectedAttr.value}"`)
  const prefix = parts.length ? `${parts.join('、')}，` : ''
  return `${prefix}共匹配到 ${total.value} 个技能`
})

function onTypeChange(e: any) {
  const idx = Number(e.detail.value)
  selectedType.value = idx === 0 ? '' : (skillTypes.value[idx - 1] ?? '')
}

function toggleAttr(attrName: string) {
  selectedAttr.value = selectedAttr.value === attrName ? '' : attrName
}

async function loadSkills() {
  loading.value = true
  error.value = ''
  try {
    const query: SkillQuery = {}
    const name = keyword.value.trim()
    if (name) query.name = name
    if (selectedType.value) query.skill_type = selectedType.value
    if (selectedAttr.value) query.attr = selectedAttr.value

    const res = await fetchSkills(query)
    skills.value = res.items
    total.value = res.total
    hasLoaded.value = true
  } catch {
    error.value = '查询失败，请稍后再试'
    skills.value = []
    total.value = 0
    hasLoaded.value = true
  } finally {
    loading.value = false
  }
}

function onSearchConfirm() {
  void loadSkills()
}

watch(keyword, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void loadSkills(), 300)
})

watch([selectedType, selectedAttr], () => {
  void loadSkills()
})

onLoad(async () => {
  const [attrs, types] = await Promise.all([
    fetchAttributes().catch(() => [] as Attribute[]),
    fetchSkillTypes().catch(() => [] as string[]),
  ])
  attributes.value = attrs
  skillTypes.value = types
  await loadSkills()
})
</script>

<template>
  <view class="page">
    <view class="search-card">
      <view class="search-row">
        <input
          v-model="keyword"
          class="search-input"
          confirm-type="search"
          placeholder="搜索技能名称"
          @confirm="onSearchConfirm"
        />
        <picker :range="typePickerRange" :value="typePickerIndex" @change="onTypeChange">
          <view class="type-picker-btn">
            {{ selectedType || '全部类型' }}
            <text class="picker-arrow">▼</text>
          </view>
        </picker>
      </view>
    </view>

    <view class="filter-card">
      <view class="section-head">
        <text class="section-title">属性筛选</text>
        <text class="section-tip" v-if="selectedAttr">当前：{{ selectedAttr }}</text>
      </view>
      <scroll-view class="attr-scroll" scroll-x>
        <view class="attr-list">
          <view
            class="attr-pill"
            :class="{ active: selectedAttr === '' }"
            @tap="toggleAttr('')"
          >
            全部
          </view>
          <view
            v-for="attr in attributes"
            :key="attr.attr_name"
            class="attr-pill"
            :class="{ active: selectedAttr === attr.attr_name }"
            @tap="toggleAttr(attr.attr_name)"
          >
            <image
              v-if="attr.attr_image"
              class="attr-pill-icon"
              :src="attr.attr_image"
              mode="aspectFit"
            />
            <text>{{ attr.attr_name }}</text>
          </view>
        </view>
      </scroll-view>
    </view>

    <view v-if="hasLoaded" class="summary-row">
      <text class="summary-text">{{ summaryText }}</text>
    </view>

    <view v-if="error" class="error-box">
      <text>{{ error }}</text>
    </view>

    <view v-if="loading && !hasLoaded" class="skeleton-list">
      <view v-for="n in 6" :key="n" class="skeleton-item" />
    </view>

    <view v-else-if="skills.length === 0 && hasLoaded && !error" class="empty-box">
      <text class="empty-title">没有找到匹配的技能</text>
      <text class="empty-tip">试试换个关键词或筛选条件</text>
    </view>

    <view v-else class="skill-list">
      <view v-for="item in skills" :key="item.name" class="skill-card">
        <view class="skill-icon-wrap">
          <image v-if="item.icon" class="skill-icon" :src="item.icon" mode="aspectFit" />
          <view v-else class="skill-icon-placeholder">?</view>
        </view>
        <view class="skill-body">
          <text class="skill-name">{{ item.name }}</text>
          <view class="skill-tags">
            <text v-if="item.attr" class="tag tag-attr">{{ item.attr }}</text>
            <text v-if="item.type" class="tag tag-type">{{ item.type }}</text>
          </view>
          <view class="skill-stats">
            <text v-if="item.power" class="stat-text">威力 {{ item.power }}</text>
            <text v-if="item.consume" class="stat-text">消耗 {{ item.consume }}</text>
          </view>
          <text v-if="item.desc" class="skill-desc">{{ item.desc }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 24rpx;
  background: linear-gradient(180deg, #f3f8ff 0%, #f9fbff 100%);
}

.search-card,
.filter-card,
.empty-box,
.error-box {
  margin-bottom: 24rpx;
  padding: 28rpx;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 12rpx 32rpx rgba(64, 125, 255, 0.08);
}

.search-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.search-input {
  flex: 1;
  height: 78rpx;
  padding: 0 24rpx;
  border-radius: 999rpx;
  background: #f3f8ff;
  font-size: 28rpx;
  color: #1e3557;
}

.type-picker-btn {
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 0 24rpx;
  height: 78rpx;
  line-height: 78rpx;
  border-radius: 999rpx;
  background: #eef4ff;
  font-size: 24rpx;
  color: #45638e;
  white-space: nowrap;
}

.picker-arrow {
  font-size: 20rpx;
  color: #8aa2c9;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 20rpx;
}

.section-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #214887;
}

.section-tip {
  font-size: 22rpx;
  color: #5a81c9;
}

.attr-scroll {
  white-space: nowrap;
}

.attr-list {
  display: inline-flex;
  align-items: center;
  gap: 16rpx;
  padding-bottom: 4rpx;
}

.attr-pill {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  padding: 14rpx 22rpx;
  border-radius: 999rpx;
  background: #eef4ff;
  color: #45638e;
  font-size: 24rpx;
  white-space: nowrap;
}

.attr-pill.active {
  background: linear-gradient(135deg, #2b74ff 0%, #53a0ff 100%);
  color: #ffffff;
}

.attr-pill-icon {
  width: 28rpx;
  height: 28rpx;
}

.summary-row {
  margin-bottom: 20rpx;
}

.summary-text {
  font-size: 24rpx;
  color: #7a93bb;
}

.error-box {
  color: #c74646;
  background: #fff2f2;
}

.empty-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12rpx;
  padding: 80rpx 36rpx;
}

.empty-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #284974;
}

.empty-tip {
  font-size: 24rpx;
  color: #7a93bb;
}

.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.skeleton-item {
  height: 180rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #edf4ff 0%, #ffffff 100%);
}

.skill-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.skill-card {
  display: flex;
  gap: 20rpx;
  align-items: flex-start;
  padding: 24rpx;
  border-radius: 24rpx;
  background: #ffffff;
  box-shadow: 0 8rpx 24rpx rgba(64, 125, 255, 0.06);
}

.skill-icon-wrap {
  width: 80rpx;
  height: 80rpx;
  border-radius: 16rpx;
  background: #f3f8ff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.skill-icon {
  width: 56rpx;
  height: 56rpx;
}

.skill-icon-placeholder {
  font-size: 32rpx;
  color: #b5c8e8;
}

.skill-body {
  flex: 1;
  min-width: 0;
}

.skill-name {
  display: block;
  font-size: 28rpx;
  font-weight: 700;
  color: #1f3760;
  margin-bottom: 10rpx;
}

.skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-bottom: 10rpx;
}

.tag {
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
}

.tag-attr {
  color: #45638e;
  background: #edf3ff;
}

.tag-type {
  color: #7d56d6;
  background: rgba(125, 86, 214, 0.12);
}

.skill-stats {
  display: flex;
  gap: 24rpx;
  margin-bottom: 8rpx;
}

.stat-text {
  font-size: 22rpx;
  color: #7a93bb;
}

.skill-desc {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 24rpx;
  line-height: 1.7;
  color: #6f89b2;
}
</style>
