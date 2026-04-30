<script setup lang="ts">
interface MenuItem {
  title: string
  desc: string
  url: string
  color: string
}

const menuItems: MenuItem[] = [
  {
    title: '孵蛋查询',
    desc: '输入身高体重，匹配对应宠物',
    url: '/pages/pokemon/body-match',
    color: '#2b74ff',
  },
  {
    title: '技能石查询',
    desc: '按技能名查找技能石获取方式',
    url: '/pages/skill/stone',
    color: '#18a874',
  },
  {
    title: '名词解释',
    desc: '印记、状态、环境等战斗术语说明',
    url: '/pages/more/pokemon-marks',
    color: '#f08b3a',
  },
  {
    title: '精灵蛋查询',
    desc: '查看可孵化精灵蛋及其对应宠物',
    url: '/pages/more/pokemon-eggs',
    color: '#9c5bff',
  },
  {
    title: '宠物果实查询',
    desc: '查看宠物果实图鉴',
    url: '/pages/more/pokemon-fruits',
    color: '#ff6b9c',
  },
]

function goBattlePk() {
  uni.navigateTo({ url: '/pages/battle-pk/index' })
}

function navigateTo(url: string) {
  uni.navigateTo({ url })
}
</script>

<template>
  <view class="page">
    <view class="hero-card">
      <text class="hero-title">更多工具</text>
      <text class="hero-subtitle">快捷入口，查询更多游戏数据。</text>
    </view>

    <view class="pk-card" @tap="goBattlePk">
      <view class="pk-content">
        <text class="pk-title">阵容 PK · 模拟对战</text>
        <text class="pk-desc">配置两套队伍，按经典回合制规则推演胜率与回合节奏</text>
      </view>
      <text class="pk-arrow">›</text>
    </view>

    <view class="menu-list">
      <view
        v-for="item in menuItems"
        :key="item.url"
        class="menu-card"
        @tap="navigateTo(item.url)"
      >
        <view class="menu-dot" :style="{ background: item.color }" />
        <view class="menu-content">
          <text class="menu-title">{{ item.title }}</text>
          <text class="menu-desc">{{ item.desc }}</text>
        </view>
        <text class="menu-arrow">›</text>
      </view>
    </view>

    <view class="about-card">
      <text class="about-title">关于</text>
      <text class="about-text">洛克王国精灵图鉴小程序</text>
      <text class="about-text">数据来源于游戏攻略站，仅供参考。</text>
    </view>
  </view>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 24rpx;
  background: linear-gradient(180deg, #f3f8ff 0%, #f9fbff 100%);
}

.hero-card {
  margin-bottom: 24rpx;
  padding: 36rpx 28rpx;
  border-radius: 28rpx;
  background: linear-gradient(135deg, #2b74ff 0%, #53a0ff 100%);
  box-shadow: 0 12rpx 32rpx rgba(43, 116, 255, 0.2);
}

.hero-title {
  display: block;
  font-size: 40rpx;
  font-weight: 700;
  color: #ffffff;
}

.hero-subtitle {
  display: block;
  margin-top: 10rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.8);
}

.pk-card {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 28rpx;
  margin-bottom: 24rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #2b74ff 0%, #f56c6c 100%);
  box-shadow: 0 12rpx 28rpx rgba(43, 116, 255, 0.22);
}

.pk-content { flex: 1; min-width: 0; }
.pk-title {
  display: block;
  font-size: 32rpx;
  font-weight: 700;
  color: #ffffff;
}
.pk-desc {
  display: block;
  margin-top: 6rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.85);
  line-height: 1.5;
}
.pk-arrow {
  font-size: 40rpx;
  color: rgba(255, 255, 255, 0.85);
  flex-shrink: 0;
}

.menu-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
  margin-bottom: 24rpx;
}

.menu-card {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 28rpx;
  border-radius: 24rpx;
  background: #ffffff;
  box-shadow: 0 8rpx 24rpx rgba(64, 125, 255, 0.06);
}

.menu-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  flex-shrink: 0;
}

.menu-content {
  flex: 1;
  min-width: 0;
}

.menu-title {
  display: block;
  font-size: 30rpx;
  font-weight: 700;
  color: #1f3760;
}

.menu-desc {
  display: block;
  margin-top: 6rpx;
  font-size: 24rpx;
  color: #7a93bb;
}

.menu-arrow {
  font-size: 36rpx;
  color: #b5c8e8;
  flex-shrink: 0;
}

.about-card {
  padding: 28rpx;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 8rpx 24rpx rgba(64, 125, 255, 0.06);
}

.about-title {
  display: block;
  font-size: 28rpx;
  font-weight: 700;
  color: #214887;
  margin-bottom: 14rpx;
}

.about-text {
  display: block;
  font-size: 24rpx;
  line-height: 1.8;
  color: #7a93bb;
}
</style>
