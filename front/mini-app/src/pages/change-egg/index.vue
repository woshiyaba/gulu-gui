<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import {
  fetchMyListings,
  closeListing,
  deleteListing,
  type ChangeEggListing,
  type ChangeEggStatus,
} from '@/api/changeEgg'
import { fetchUnreadCount, refreshMoreTabRedDot } from '@/api/message'
import { getStoredUserId } from '@/utils/auth'

interface StatusTab {
  label: string
  value: ChangeEggStatus | ''
}

const STATUS_TABS: StatusTab[] = [
  { label: '全部', value: '' },
  { label: '匹配中', value: 'open' },
  { label: '已匹配', value: 'matched' },
  { label: '已关闭', value: 'closed' },
]

const STATUS_TEXT: Record<string, string> = {
  open: '匹配中',
  matched: '已匹配',
  closed: '已关闭',
}

const userId = ref(getStoredUserId())
const activeStatus = ref<ChangeEggStatus | ''>('')
const listings = ref<ChangeEggListing[]>([])
const loading = ref(false)
const error = ref('')
const hasLoaded = ref(false)
const unread = ref(0)

const isLoggedIn = computed(() => !!userId.value)

async function loadListings() {
  if (!isLoggedIn.value) {
    error.value = '请先在小程序内登录后再使用换蛋广场'
    return
  }
  loading.value = true
  error.value = ''
  try {
    listings.value = await fetchMyListings(userId.value, activeStatus.value || undefined)
    hasLoaded.value = true
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
}

async function refreshUnread() {
  if (!isLoggedIn.value) return
  try {
    const res = await fetchUnreadCount(userId.value)
    unread.value = res.count
  } catch {
    unread.value = 0
  }
  void refreshMoreTabRedDot()
}

function selectStatus(value: ChangeEggStatus | '') {
  if (activeStatus.value === value) return
  activeStatus.value = value
  void loadListings()
}

function goPublish() {
  uni.navigateTo({ url: '/pages/change-egg/publish' })
}

function goMessages() {
  uni.navigateTo({ url: '/pages/change-egg/messages' })
}

async function handleClose(item: ChangeEggListing) {
  const res = await uni.showModal({ title: '关闭挂单', content: '关闭后将不再参与匹配，确定吗？' })
  if (!res.confirm) return
  try {
    await closeListing(item.id, userId.value)
    uni.showToast({ title: '已关闭', icon: 'success' })
    void loadListings()
  } catch (err) {
    uni.showToast({ title: err instanceof Error ? err.message : '关闭失败', icon: 'none' })
  }
}

async function handleDelete(item: ChangeEggListing) {
  const res = await uni.showModal({ title: '删除挂单', content: '删除后无法恢复，确定删除吗？' })
  if (!res.confirm) return
  try {
    await deleteListing(item.id, userId.value)
    uni.showToast({ title: '已删除', icon: 'success' })
    void loadListings()
  } catch (err) {
    uni.showToast({ title: err instanceof Error ? err.message : '删除失败', icon: 'none' })
  }
}

onShow(() => {
  userId.value = getStoredUserId()
  void loadListings()
  void refreshUnread()
})
</script>

<template>
  <view class="page">
    <view class="hero-card">
      <view class="hero-main">
        <text class="hero-title">匹配换蛋</text>
        <text class="hero-subtitle">发布你拥有 / 想要的蛋组，系统自动为你寻找互换对象。</text>
      </view>
      <view class="bell" @tap="goMessages">
        <text class="bell-icon">💬</text>
        <view v-if="unread > 0" class="bell-dot">
          <text class="bell-dot-text">{{ unread > 99 ? '99+' : unread }}</text>
        </view>
      </view>
    </view>

    <view class="publish-card" @tap="goPublish">
      <view class="publish-content">
        <text class="publish-title">+ 发布换蛋</text>
        <text class="publish-desc">选择拥有 / 想要的精灵蛋组，立即开始匹配</text>
      </view>
      <text class="publish-arrow">›</text>
    </view>

    <view class="tabs">
      <view
        v-for="tab in STATUS_TABS"
        :key="tab.value"
        class="tab"
        :class="{ active: activeStatus === tab.value }"
        @tap="selectStatus(tab.value)"
      >
        <text class="tab-text">{{ tab.label }}</text>
      </view>
    </view>

    <view v-if="error" class="error-box">
      <text>{{ error }}</text>
    </view>

    <view v-if="loading && listings.length === 0" class="tip-box">
      <text class="tip-text">加载中...</text>
    </view>

    <view v-else-if="hasLoaded && listings.length === 0 && !error" class="empty-box">
      <text class="empty-title">还没有相关挂单</text>
      <text class="empty-tip">点击上方「发布换蛋」开始匹配吧</text>
    </view>

    <view v-else class="list">
      <view v-for="item in listings" :key="item.id" class="listing-card">
        <view class="listing-head">
          <view class="status-badge" :class="`status-${item.status}`">
            <text class="status-text">{{ STATUS_TEXT[item.status] || item.status }}</text>
          </view>
          <text class="game-id">游戏ID：{{ item.game_id || '未填写' }}</text>
        </view>

        <view class="exchange">
          <view class="side">
            <text class="side-label">我拥有</text>
            <image
              v-if="item.own_pokemon_avatar"
              class="side-avatar"
              :src="item.own_pokemon_avatar"
              mode="aspectFit"
            />
            <view v-else class="side-avatar placeholder">?</view>
            <text class="side-name">{{ item.own_pokemon_name || ('#' + item.own_pokemon_id) }}</text>
            <text v-if="item.own_tag" class="side-tag">{{ item.own_tag }}</text>
          </view>

          <text class="swap-icon">⇄</text>

          <view class="side">
            <text class="side-label">我想要</text>
            <image
              v-if="item.want_pokemon_avatar"
              class="side-avatar"
              :src="item.want_pokemon_avatar"
              mode="aspectFit"
            />
            <view v-else class="side-avatar placeholder">?</view>
            <text class="side-name">{{ item.want_pokemon_name || ('#' + item.want_pokemon_id) }}</text>
            <text v-if="item.want_tag" class="side-tag">{{ item.want_tag }}</text>
          </view>
        </view>

        <view class="actions">
          <view
            v-if="item.status === 'open'"
            class="action-btn close-btn"
            @tap="handleClose(item)"
          >
            <text>关闭</text>
          </view>
          <view class="action-btn delete-btn" @tap="handleDelete(item)">
            <text>删除</text>
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
  background: linear-gradient(180deg, #f3f8ff 0%, #f9fbff 100%);
}

.hero-card {
  position: relative;
  display: flex;
  align-items: flex-start;
  margin-bottom: 24rpx;
  padding: 36rpx 28rpx;
  border-radius: 28rpx;
  background: linear-gradient(135deg, #9c5bff 0%, #53a0ff 100%);
  box-shadow: 0 12rpx 32rpx rgba(108, 99, 255, 0.22);
}
.hero-main { flex: 1; min-width: 0; padding-right: 96rpx; }
.hero-title { display: block; font-size: 40rpx; font-weight: 700; color: #ffffff; }
.hero-subtitle {
  display: block;
  margin-top: 10rpx;
  font-size: 24rpx;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.85);
}

.bell {
  position: absolute;
  top: 28rpx;
  right: 28rpx;
  width: 72rpx;
  height: 72rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.22);
  display: flex;
  align-items: center;
  justify-content: center;
}
.bell-icon { font-size: 36rpx; }
.bell-dot {
  position: absolute;
  top: -6rpx;
  right: -6rpx;
  min-width: 32rpx;
  height: 32rpx;
  padding: 0 8rpx;
  border-radius: 999rpx;
  background: #ff4d4f;
  display: flex;
  align-items: center;
  justify-content: center;
}
.bell-dot-text { font-size: 20rpx; color: #ffffff; font-weight: 700; }

.publish-card {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 28rpx;
  margin-bottom: 24rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #2b74ff 0%, #18a874 100%);
  box-shadow: 0 12rpx 28rpx rgba(43, 116, 255, 0.2);
}
.publish-content { flex: 1; min-width: 0; }
.publish-title { display: block; font-size: 32rpx; font-weight: 700; color: #ffffff; }
.publish-desc {
  display: block;
  margin-top: 6rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.85);
}
.publish-arrow { font-size: 40rpx; color: rgba(255, 255, 255, 0.85); }

.tabs {
  display: flex;
  gap: 14rpx;
  margin-bottom: 24rpx;
}
.tab {
  padding: 12rpx 28rpx;
  border-radius: 999rpx;
  background: #ffffff;
  box-shadow: 0 6rpx 16rpx rgba(64, 125, 255, 0.06);
}
.tab.active { background: #2b74ff; }
.tab-text { font-size: 26rpx; color: #5a76a8; }
.tab.active .tab-text { color: #ffffff; font-weight: 700; }

.error-box,
.tip-box,
.empty-box {
  padding: 48rpx 28rpx;
  border-radius: 24rpx;
  background: #ffffff;
  box-shadow: 0 8rpx 24rpx rgba(64, 125, 255, 0.06);
  text-align: center;
}
.error-box { color: #c74646; background: #fff2f2; }
.tip-text { font-size: 26rpx; color: #7a93bb; }
.empty-box { display: flex; flex-direction: column; gap: 12rpx; }
.empty-title { font-size: 30rpx; font-weight: 700; color: #284974; }
.empty-tip { font-size: 24rpx; color: #7a93bb; }

.list { display: flex; flex-direction: column; gap: 20rpx; }

.listing-card {
  padding: 24rpx;
  border-radius: 24rpx;
  background: #ffffff;
  box-shadow: 0 8rpx 24rpx rgba(64, 125, 255, 0.08);
}

.listing-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18rpx;
}
.status-badge { padding: 6rpx 18rpx; border-radius: 999rpx; }
.status-open { background: #e4efff; }
.status-open .status-text { color: #2b74ff; }
.status-matched { background: #e1f7ec; }
.status-matched .status-text { color: #18a874; }
.status-closed { background: #f0f0f4; }
.status-closed .status-text { color: #8a93a6; }
.status-text { font-size: 22rpx; font-weight: 700; }
.game-id { font-size: 22rpx; color: #7a93bb; }

.exchange {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
}
.side {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6rpx;
}
.side-label { font-size: 22rpx; color: #7a93bb; }
.side-avatar {
  width: 96rpx;
  height: 96rpx;
  border-radius: 16rpx;
  background: linear-gradient(180deg, #edf5ff 0%, #f8fbff 100%);
}
.side-avatar.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40rpx;
  color: #b6c7e7;
}
.side-name {
  font-size: 26rpx;
  font-weight: 700;
  color: #1f3760;
  text-align: center;
}
.side-tag {
  padding: 2rpx 14rpx;
  border-radius: 999rpx;
  background: #fff4e4;
  font-size: 20rpx;
  color: #f08b3a;
}
.swap-icon { font-size: 40rpx; color: #9c5bff; flex-shrink: 0; }

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 16rpx;
  margin-top: 22rpx;
}
.action-btn {
  padding: 12rpx 32rpx;
  border-radius: 999rpx;
  border: 2rpx solid #e3eaf5;
}
.close-btn { border-color: #2b74ff; }
.close-btn text { font-size: 24rpx; color: #2b74ff; }
.delete-btn { border-color: #f0a3a3; }
.delete-btn text { font-size: 24rpx; color: #e25555; }
</style>
