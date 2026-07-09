<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { fetchAbout, fetchChangeEggEntrySwitch } from '@/api/pokemon'
import { refreshMoreTabRedDot } from '@/api/message'

interface MenuItem {
  title: string
  desc: string
  url: string
  color: string
}

const DEFAULT_ABOUT = ['洛克王国精灵图鉴小程序', '数据来源于游戏攻略站，仅供参考。']

const aboutTexts = ref<string[]>([])
const isChangeEggEntryVisible = ref(false)

// 后端 label 可能用 \n 表示换行，逐条拆分成多行展示。
const aboutLines = computed(() => {
  const source = aboutTexts.value.length ? aboutTexts.value : DEFAULT_ABOUT
  return source.flatMap((text) => text.split('\n')).filter((line) => line.trim())
})

async function loadAbout() {
  try {
    const res = await fetchAbout()
    aboutTexts.value = res?.texts ?? []
  } catch {
    aboutTexts.value = []
  }
}

async function loadChangeEggEntrySwitch() {
  try {
    const res = await fetchChangeEggEntrySwitch()
    isChangeEggEntryVisible.value = res?.enabled === true
  } catch {
    isChangeEggEntryVisible.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadAbout(), loadChangeEggEntrySwitch()])
})

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
    title: '伤害计算',
    desc: '估算技能 PVP 伤害，支持克制与各类加成',
    url: '/pages/more/damage-calc',
    color: '#f5564a',
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
  {
    title: '洛克纪年',
    desc: '时间脉络回顾洛克王国大事记',
    url: '/pages/more/chronology',
    color: '#16b8a6',
  },
  {
    title: '意见反馈',
    desc: '提交使用建议或问题，帮助我们改进',
    url: '/pages/more/feedback',
    color: '#2b74ff',
  },
]

function goBattlePk() {
  uni.navigateTo({ url: '/pages/battle-pk/index' })
}

function goChangeEgg() {
  uni.navigateTo({ url: '/pages/change-egg/index' })
}

function navigateTo(url: string) {
  uni.navigateTo({ url })
}

// 每次进入「更多」页时刷新底部红点（有未读换蛋通知 / 私聊时提醒）
onShow(() => {
  void refreshMoreTabRedDot()
  void loadChangeEggEntrySwitch()
})
</script>

<template>
  <view class="page">
    <view class="pk-card" @tap="goBattlePk">
      <view class="pk-content">
        <text class="pk-title">阵容 PK · 模拟对战</text>
        <text class="pk-desc">配置两套队伍，按经典回合制规则推演胜率与回合节奏</text>
      </view>
      <text class="pk-arrow">›</text>
    </view>

    <view v-if="isChangeEggEntryVisible" class="egg-card" @tap="goChangeEgg">
      <view class="pk-content">
        <text class="pk-title">匹配换蛋 · 蛋组互换</text>
        <text class="pk-desc">发布拥有 / 想要的蛋组，系统自动匹配互换对象并消息提醒</text>
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
      <text v-for="(line, idx) in aboutLines" :key="idx" class="about-text">{{ line }}</text>
    </view>
  </view>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 24rpx;
  background: linear-gradient(180deg, #f3f8ff 0%, #f9fbff 100%);
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

.egg-card {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 28rpx;
  margin-bottom: 24rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #9c5bff 0%, #53a0ff 100%);
  box-shadow: 0 12rpx 28rpx rgba(108, 99, 255, 0.22);
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
