<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchAnnouncement } from '@/api/pokemon'
import type { Announcement } from '@/types/announcement'

// 「不再展示」记录的版本号；后台更新公告后版本变化，已关闭的公告会重新弹出。
const DISMISS_KEY = 'roco_announce_dismiss'

const visible = ref(false)
const announcement = ref<Announcement | null>(null)

// 公告更新时间作为版本号；无更新时间则用标题+内容兜底。
function versionOf(a: Announcement): string {
  return a.updated_at || `${a.title}|${a.content}`
}

function readDismissedVersion(): string {
  try {
    return uni.getStorageSync(DISMISS_KEY) || ''
  } catch {
    return ''
  }
}

function shouldShow(a: Announcement): boolean {
  return readDismissedVersion() !== versionOf(a)
}

async function load() {
  try {
    const a = await fetchAnnouncement()
    // 后台未启用或内容为空时接口返回 null，不展示弹窗。
    if (!a || (!a.title && !a.content)) return
    announcement.value = a
    if (shouldShow(a)) visible.value = true
  } catch {
    // 公告拉取失败不影响首页其余功能
  }
}

// 本次关闭，下次进入仍会提示
function close() {
  visible.value = false
}

// 不再展示：记录当前版本，相同公告不再弹出
function dismissForever() {
  const a = announcement.value
  if (a) {
    try {
      uni.setStorageSync(DISMISS_KEY, versionOf(a))
    } catch {
      // 存储失败时仅关闭，不影响使用
    }
  }
  visible.value = false
}

onMounted(load)
</script>

<template>
  <view v-if="visible && announcement" class="announce-mask" @tap.self="close">
    <view class="announce-card">
      <view class="announce-header">
        <text class="announce-title">📢 {{ announcement.title || '公告' }}</text>
        <text class="announce-close" @tap="close">✕</text>
      </view>

      <scroll-view scroll-y class="announce-body">
        <text class="announce-content">{{ announcement.content }}</text>
      </scroll-view>

      <view class="announce-footer">
        <text class="announce-skip" @tap="dismissForever">不再展示</text>
        <view class="announce-btn" @tap="close">
          <text class="announce-btn-text">我知道了</text>
        </view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.announce-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48rpx;
  z-index: 1000;
}

.announce-card {
  width: 100%;
  max-width: 620rpx;
  max-height: 76vh;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 28rpx;
  overflow: hidden;
  box-shadow: 0 24rpx 64rpx rgba(15, 23, 42, 0.28);
}

.announce-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  padding: 28rpx 32rpx;
  border-bottom: 2rpx solid #eef2f8;
}

.announce-title {
  flex: 1;
  min-width: 0;
  font-size: 32rpx;
  font-weight: 700;
  color: #2b74ff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.announce-close {
  padding: 4rpx 8rpx;
  font-size: 30rpx;
  color: #9aa7bd;
  line-height: 1;
}

.announce-body {
  flex: 1 1 auto;
  min-height: 0;
  box-sizing: border-box;
  padding: 28rpx 32rpx;
}

.announce-content {
  font-size: 28rpx;
  line-height: 1.7;
  color: #33415c;
  white-space: pre-wrap;
  word-break: break-word;
}

.announce-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  padding: 24rpx 32rpx;
  border-top: 2rpx solid #eef2f8;
}

.announce-skip {
  font-size: 26rpx;
  color: #8a99b3;
}

.announce-btn {
  padding: 14rpx 40rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #2b74ff 0%, #53a0ff 100%);
}

.announce-btn-text {
  font-size: 28rpx;
  color: #ffffff;
}
</style>
