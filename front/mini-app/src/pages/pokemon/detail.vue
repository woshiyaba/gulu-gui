<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { fetchPokemonDetail, fetchPokemonEvolutionChain } from '@/api/pokemon'
import type { PokemonDetail, PokemonEvolutionChain } from '@/types/pokemon'

const pokemon = ref<PokemonDetail | null>(null)
const evolutionChain = ref<PokemonEvolutionChain | null>(null)
const loading = ref(true)
const error = ref('')

const STAT_CONFIGS = [
  { key: 'hp', label: 'HP', color: 'linear-gradient(90deg, #35c88a 0%, #7be6b4 100%)' },
  { key: 'atk', label: '物攻', color: 'linear-gradient(90deg, #ff7d7d 0%, #ffb36f 100%)' },
  { key: 'matk', label: '魔攻', color: 'linear-gradient(90deg, #a774ff 0%, #cc9dff 100%)' },
  { key: 'def_val', label: '物防', color: 'linear-gradient(90deg, #4d8eff 0%, #7bb0ff 100%)' },
  { key: 'mdef', label: '魔防', color: 'linear-gradient(90deg, #6172ff 0%, #97a4ff 100%)' },
  { key: 'spd', label: '速度', color: 'linear-gradient(90deg, #ffb938 0%, #ffd97b 100%)' },
] as const

function statPercent(value: number) {
  return `${Math.min(100, Math.round((value / 500) * 100))}%`
}

function goBack() {
  if (getCurrentPages().length > 1) {
    uni.navigateBack()
    return
  }

  uni.reLaunch({
    url: '/pages/index/index',
  })
}

function isCurrentEvolutionItem(name: string) {
  return pokemon.value?.name === name
}

function goToEvolution(name: string) {
  if (pokemon.value?.name === name) return
  uni.redirectTo({
    url: `/pages/pokemon/detail?name=${encodeURIComponent(name)}`,
  })
}

function previewImage(url: string) {
  if (!url) return

  uni.previewImage({
    urls: [url],
  })
}

async function loadDetail(name: string) {
  loading.value = true
  error.value = ''

  try {
    const [detail, chain] = await Promise.all([
      fetchPokemonDetail(name),
      fetchPokemonEvolutionChain(name),
    ])
    pokemon.value = detail
    evolutionChain.value = chain
    uni.setNavigationBarTitle({
      title: detail.name,
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '宠物详情加载失败'
  } finally {
    loading.value = false
  }
}

onLoad((options) => {
  // 量体查宠传 pet_name；图鉴列表传 name，二者取其一
  const rawPetName = typeof options?.pet_name === 'string' ? options.pet_name : ''
  const rawName = typeof options?.name === 'string' ? options.name : ''
  const pokemonName = decodeURIComponent(rawPetName || rawName)

  if (!pokemonName) {
    error.value = '缺少宠物名称，暂时无法加载详情。'
    loading.value = false
    return
  }

  void loadDetail(pokemonName)
})
</script>

<template>
  <view class="page">
    <view class="top-actions">
      <button class="back-button" @tap="goBack">返回图鉴</button>
    </view>

    <view v-if="loading" class="state-card">
      <text class="state-text">详情加载中...</text>
    </view>

    <view v-else-if="error" class="error-card">
      <text class="error-text">{{ error }}</text>
    </view>

    <view v-else-if="pokemon" class="content">
      <view class="hero-card">
        <view class="hero-image-wrap" @tap="previewImage(pokemon.image_url)">
          <image
            v-if="pokemon.image_url"
            class="hero-image"
            :src="pokemon.image_url"
            mode="aspectFit"
          />
          <view v-else class="hero-placeholder">?</view>
        </view>

        <view class="hero-info">
          <text class="pokemon-no">#{{ pokemon.no || '--' }}</text>
          <text class="pokemon-name">{{ pokemon.name }}</text>

          <view class="badge-row">
            <text v-if="pokemon.type_name" class="badge type-badge">{{ pokemon.type_name }}</text>
            <text v-if="pokemon.form_name" class="badge form-badge">{{ pokemon.form_name }}</text>
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

          <view class="obtain-card">
            <text class="obtain-label">获取方式</text>
            <text class="obtain-value">{{ pokemon.obtain_method || '暂无数据' }}</text>
          </view>
        </view>
      </view>

      <view class="section-card">
        <text class="section-title">种族值</text>
        <view class="stats-list">
          <view
            v-for="config in STAT_CONFIGS"
            :key="config.key"
            class="stat-item"
          >
            <view class="stat-head">
              <text class="stat-label">{{ config.label }}</text>
              <text class="stat-value">{{ pokemon.stats[config.key] }}</text>
            </view>
            <view class="stat-track">
              <view
                class="stat-fill"
                :style="{ width: statPercent(pokemon.stats[config.key]), background: config.color }"
              />
            </view>
          </view>
        </view>
      </view>

      <view v-if="pokemon.trait.name" class="section-card">
        <text class="section-title">特性</text>
        <text class="trait-name">{{ pokemon.trait.name }}</text>
        <text class="trait-desc">{{ pokemon.trait.desc || '暂无描述' }}</text>
      </view>

      <view class="section-card">
        <text class="section-title">进化链</text>
        <view v-if="!evolutionChain?.stages?.length" class="evo-empty">
          <text class="empty-text">暂无进化链数据</text>
        </view>
        <view v-else class="evo-stages">
          <template v-for="(stage, index) in evolutionChain.stages" :key="stage.sort_order">
            <view class="evo-stage">
              <view class="evo-items">
                <view
                  v-for="item in stage.items"
                  :key="item.name"
                  class="evo-item"
                  :class="{ 'evo-item-active': isCurrentEvolutionItem(item.name) }"
                  @tap="goToEvolution(item.name)"
                >
                  <view class="evo-img-wrap">
                    <image
                      v-if="item.image_url"
                      class="evo-img"
                      :src="item.image_url"
                      mode="aspectFit"
                    />
                    <text v-else class="evo-img-placeholder">?</text>
                  </view>
                  <text class="evo-name">{{ item.name }}</text>
                </view>
              </view>
            </view>

            <view v-if="index < evolutionChain.stages.length - 1" class="evo-arrow-block">
              <text class="evo-arrow">↓</text>
              <text v-if="stage.next_condition" class="evo-condition">{{ stage.next_condition }}</text>
            </view>
          </template>
        </view>
      </view>

      <view v-if="pokemon.defensive_type_chart?.cells?.length" class="section-card">
        <text class="section-title">受击倍率</text>
        <text class="type-chart-tip">
          进攻招式属性与受击倍率。
        </text>
        <view class="type-chart-mobile-box">
          <view class="type-chart-mobile-def">
            <text class="type-chart-mobile-def-label">本方属性</text>
            <text class="type-chart-mobile-def-val">{{
              pokemon.defensive_type_chart.defender_attrs.join(' + ')
            }}</text>
          </view>
          <view class="type-chart-mobile-grid">
            <view
              v-for="c in pokemon.defensive_type_chart.cells"
              :key="'mg-' + c.attacker_attr"
              class="type-chart-mobile-cell"
            >
              <text class="type-chart-mobile-attr">{{ c.attacker_attr }}</text>
              <text class="type-chart-mobile-val" :class="'bucket-' + c.bucket">{{ c.label }}</text>
            </view>
          </view>
        </view>
      </view>

      <view class="section-card">
        <text class="section-title">属性克制</text>

        <view class="restrain-group" v-if="pokemon.restrain.strong_against.length">
          <text class="restrain-title strong">克制</text>
          <view class="restrain-tags">
            <text
              v-for="item in pokemon.restrain.strong_against"
              :key="item"
              class="restrain-tag strong-bg"
            >
              {{ item }}
            </text>
          </view>
        </view>

        <view class="restrain-group" v-if="pokemon.restrain.weak_against.length">
          <text class="restrain-title weak">被克制</text>
          <view class="restrain-tags">
            <text
              v-for="item in pokemon.restrain.weak_against"
              :key="item"
              class="restrain-tag weak-bg"
            >
              {{ item }}
            </text>
          </view>
        </view>

        <view class="restrain-group" v-if="pokemon.restrain.resist.length">
          <text class="restrain-title resist">抵抗</text>
          <view class="restrain-tags">
            <text
              v-for="item in pokemon.restrain.resist"
              :key="item"
              class="restrain-tag resist-bg"
            >
              {{ item }}
            </text>
          </view>
        </view>

        <view class="restrain-group" v-if="pokemon.restrain.resisted.length">
          <text class="restrain-title resisted">被抵抗</text>
          <view class="restrain-tags">
            <text
              v-for="item in pokemon.restrain.resisted"
              :key="item"
              class="restrain-tag resisted-bg"
            >
              {{ item }}
            </text>
          </view>
        </view>

        <text
          v-if="!pokemon.restrain.strong_against.length
            && !pokemon.restrain.weak_against.length
            && !pokemon.restrain.resist.length
            && !pokemon.restrain.resisted.length"
          class="empty-text"
        >
          暂无克制关系数据
        </text>
      </view>

      <view class="section-card">
        <view class="skill-head">
          <text class="section-title">技能列表</text>
          <text class="skill-count">{{ pokemon.skills.length }} 个</text>
        </view>

        <view v-if="pokemon.skills.length === 0">
          <text class="empty-text">暂无技能数据</text>
        </view>

        <view v-else class="skill-list">
          <view
            v-for="skill in pokemon.skills"
            :key="skill.name"
            class="skill-card"
          >
            <view class="skill-title-row">
              <view class="skill-name-wrap">
                <image
                  v-if="skill.icon"
                  class="skill-icon"
                  :src="skill.icon"
                  mode="aspectFit"
                />
                <text class="skill-name">{{ skill.name }}</text>
              </view>
              <view class="skill-meta-row">
                <text v-if="skill.attr" class="skill-meta attr-meta">{{ skill.attr }}</text>
                <text v-if="skill.type" class="skill-meta type-meta">{{ skill.type }}</text>
              </view>
            </view>

            <view class="skill-data-row">
              <text class="skill-data">威力：{{ skill.power || '—' }}</text>
              <text class="skill-data">消耗：{{ skill.consume || '—' }}</text>
            </view>

            <text class="skill-desc">{{ skill.desc || '暂无描述' }}</text>
          </view>
        </view>
      </view>
    </view>
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

.content {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.hero-card,
.section-card,
.state-card,
.error-card {
  padding: 28rpx;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 12rpx 32rpx rgba(64, 125, 255, 0.08);
}

.state-card,
.error-card {
  text-align: center;
}

.state-text {
  font-size: 28rpx;
  color: #6d87b1;
}

.error-text {
  font-size: 28rpx;
  line-height: 1.7;
  color: #c74646;
}

.hero-card {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.hero-image-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 320rpx;
  border-radius: 24rpx;
  background: linear-gradient(180deg, #edf5ff 0%, #f9fbff 100%);
}

.hero-image {
  width: 250rpx;
  height: 250rpx;
}

.hero-placeholder {
  font-size: 92rpx;
  color: #b5c8e8;
}

.hero-info {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.pokemon-no {
  font-size: 22rpx;
  color: #8aa2c9;
}

.pokemon-name {
  font-size: 44rpx;
  font-weight: 700;
  color: #1f3760;
}

.badge-row,
.attr-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}

.badge {
  padding: 8rpx 16rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
}

.type-badge {
  color: #2761d8;
  background: rgba(39, 97, 216, 0.12);
}

.form-badge {
  color: #169b7b;
  background: rgba(22, 155, 123, 0.12);
}

.attr-chip {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  padding: 8rpx 16rpx;
  border-radius: 999rpx;
  background: #eef4ff;
}

.attr-icon {
  width: 28rpx;
  height: 28rpx;
}

.attr-text {
  font-size: 22rpx;
  color: #45638e;
}

.obtain-card {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
  padding: 22rpx;
  border-radius: 22rpx;
  background: #f6f9ff;
}

.obtain-label {
  font-size: 22rpx;
  color: #7d94ba;
}

.obtain-value {
  font-size: 26rpx;
  line-height: 1.7;
  color: #314f7d;
}

.section-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #214887;
}

.stats-list {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
  margin-top: 20rpx;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}

.stat-head {
  display: flex;
  justify-content: space-between;
  gap: 16rpx;
}

.stat-label {
  font-size: 24rpx;
  color: #5a749f;
}

.stat-value {
  font-size: 24rpx;
  font-weight: 600;
  color: #23406c;
}

.stat-track {
  overflow: hidden;
  height: 16rpx;
  border-radius: 999rpx;
  background: #e7eefb;
}

.stat-fill {
  height: 100%;
  border-radius: 999rpx;
}

.trait-name {
  display: block;
  margin-top: 18rpx;
  font-size: 28rpx;
  font-weight: 700;
  color: #1f3760;
}

.trait-desc,
.empty-text {
  display: block;
  margin-top: 14rpx;
  font-size: 24rpx;
  line-height: 1.8;
  color: #6f89b2;
}

.evo-stages {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
  margin-top: 20rpx;
}

.evo-items {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 16rpx;
}

.evo-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10rpx;
  padding: 16rpx;
  border-radius: 20rpx;
  border: 2rpx solid #e7eefb;
  background: #f8fbff;
  min-width: 140rpx;
}

.evo-item-active {
  border-color: #4d8eff;
  box-shadow: 0 0 0 4rpx rgba(77, 142, 255, 0.14);
}

.evo-img-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100rpx;
  height: 100rpx;
  border-radius: 18rpx;
  background: linear-gradient(180deg, #edf5ff 0%, #f9fbff 100%);
}

.evo-img {
  width: 80rpx;
  height: 80rpx;
}

.evo-img-placeholder {
  font-size: 48rpx;
  color: #b5c8e8;
}

.evo-name {
  font-size: 22rpx;
  font-weight: 700;
  color: #1f3760;
  text-align: center;
  word-break: break-all;
}

.evo-arrow-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}

.evo-arrow {
  font-size: 40rpx;
  line-height: 1;
  color: #8aa2c9;
}

.evo-condition {
  padding: 6rpx 16rpx;
  border-radius: 999rpx;
  background: #f0f4ff;
  font-size: 20rpx;
  color: #5a749f;
  text-align: center;
}

.evo-empty {
  margin-top: 16rpx;
}

.type-chart-tip {
  display: block;
  margin-top: 12rpx;
  margin-bottom: 16rpx;
  font-size: 22rpx;
  line-height: 1.6;
  color: #6f89b2;
}

.type-chart-mobile-box {
  border: 1rpx solid #dbe4f3;
  border-radius: 16rpx;
  padding: 20rpx 16rpx 22rpx;
  background: #fff;
}

.type-chart-mobile-def {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 10rpx 16rpx;
  margin-bottom: 18rpx;
  padding-bottom: 16rpx;
  border-bottom: 1rpx solid #e7eefb;
}

.type-chart-mobile-def-label {
  font-size: 22rpx;
  color: #6f89b2;
  font-weight: 700;
}

.type-chart-mobile-def-val {
  font-size: 24rpx;
  color: #1f3760;
  font-weight: 700;
}

.type-chart-mobile-grid {
  display: grid;
  grid-template-columns: repeat(9, minmax(0, 1fr));
  gap: 10rpx 6rpx;
}

.type-chart-mobile-cell {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 12rpx 4rpx 14rpx;
  border: 1rpx solid #dbe4f3;
  border-radius: 12rpx;
  background: #f8faff;
  box-sizing: border-box;
}

.type-chart-mobile-attr {
  font-size: 20rpx;
  font-weight: 700;
  color: #23406c;
  line-height: 1.25;
  text-align: center;
  word-break: keep-all;
}

.type-chart-mobile-val {
  margin-top: 6rpx;
  font-size: 24rpx;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.bucket-super {
  color: #ef4444;
}

.bucket-neutral {
  color: #22c55e;
}

.bucket-resist {
  color: #3b82f6;
}

.bucket-immune {
  color: #1f3760;
}

.restrain-group {
  margin-top: 20rpx;
}

.restrain-title {
  display: block;
  margin-bottom: 12rpx;
  font-size: 24rpx;
  font-weight: 700;
}

.strong {
  color: #18a874;
}

.weak {
  color: #d85b5b;
}

.resist {
  color: #2b74ff;
}

.resisted {
  color: #d09a20;
}

.restrain-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}

.restrain-tag {
  padding: 8rpx 16rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
}

.strong-bg {
  color: #18a874;
  background: rgba(24, 168, 116, 0.12);
}

.weak-bg {
  color: #d85b5b;
  background: rgba(216, 91, 91, 0.12);
}

.resist-bg {
  color: #2b74ff;
  background: rgba(43, 116, 255, 0.12);
}

.resisted-bg {
  color: #d09a20;
  background: rgba(208, 154, 32, 0.12);
}

.skill-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}

.skill-count {
  font-size: 22rpx;
  color: #7d94ba;
}

.skill-list {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
  margin-top: 20rpx;
}

.skill-card {
  padding: 24rpx;
  border-radius: 24rpx;
  background: #f8fbff;
}

.skill-title-row {
  display: flex;
  flex-direction: column;
  gap: 14rpx;
}

.skill-name-wrap {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.skill-icon {
  width: 36rpx;
  height: 36rpx;
}

.skill-name {
  font-size: 28rpx;
  font-weight: 700;
  color: #1f3760;
}

.skill-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}

.skill-meta {
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
}

.attr-meta {
  color: #45638e;
  background: #edf3ff;
}

.type-meta {
  color: #7d56d6;
  background: rgba(125, 86, 214, 0.12);
}

.skill-data-row {
  display: flex;
  flex-wrap: wrap;
  gap: 24rpx;
  margin-top: 16rpx;
}

.skill-data,
.skill-desc {
  font-size: 24rpx;
  line-height: 1.8;
  color: #5f7da6;
}

.skill-desc {
  display: block;
  margin-top: 14rpx;
}
</style>
