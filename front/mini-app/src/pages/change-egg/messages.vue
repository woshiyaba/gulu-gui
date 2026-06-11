<script setup lang="ts">
import { ref } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import { fetchInbox, markMessagesRead, refreshMoreTabRedDot, type UserMessage } from '@/api/message'
import { connectUserMessageStream, type UserMessageConnection, type UserMessageEvent } from '@/utils/ws'
import { getStoredUserId } from '@/utils/auth'

const userId = ref(getStoredUserId())
const messages = ref<UserMessage[]>([])
const loading = ref(false)
const error = ref('')
let conn: UserMessageConnection | null = null

function formatTime(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso.replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function markAllRead() {
  const unreadIds = messages.value.filter((m) => !m.is_read).map((m) => m.id)
  if (!unreadIds.length) return
  try {
    await markMessagesRead(userId.value, unreadIds)
    messages.value = messages.value.map((m) => ({ ...m, is_read: true }))
  } catch {
    /* 忽略，下次进入再标记 */
  }
  void refreshMoreTabRedDot()
}

async function loadInbox() {
  if (!userId.value) {
    error.value = '请先在小程序内登录'
    return
  }
  loading.value = true
  error.value = ''
  try {
    messages.value = await fetchInbox(userId.value, 100)
    await markAllRead()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function setupStream() {
  if (!userId.value) return
  conn = connectUserMessageStream(userId.value, {
    onMessage: (event: UserMessageEvent) => {
      // 实时收到新消息：去重后插到最前，并即时标记已读（当前正在查看）
      if (messages.value.some((m) => m.id === event.id)) return
      messages.value.unshift({
        id: event.id,
        from_user_id: event.from_user_id,
        to_user_id: event.to_user_id,
        msg_type: event.type,
        content: event.content,
        payload: event.payload ?? null,
        is_delivered: true,
        delivered_at: null,
        is_read: true,
        created_at: event.created_at ?? new Date().toISOString(),
      })
      void markMessagesRead(userId.value, [event.id])
      void refreshMoreTabRedDot()
    },
  })
}

function copyGameId(gameId?: string) {
  if (!gameId) return
  uni.setClipboardData({ data: String(gameId), success: () => uni.showToast({ title: '已复制游戏ID', icon: 'none' }) })
}

onLoad(() => {
  userId.value = getStoredUserId()
  void loadInbox()
  setupStream()
})

onUnload(() => {
  conn?.close()
  conn = null
})
</script>

<template>
  <view class="page">
    <view v-if="error" class="error-box"><text>{{ error }}</text></view>

    <view v-if="loading && messages.length === 0" class="tip-box"><text class="tip-text">加载中...</text></view>

    <view v-else-if="messages.length === 0 && !error" class="empty-box">
      <text class="empty-title">暂无消息</text>
      <text class="empty-tip">换蛋匹配成功或收到私聊时会在这里提醒你</text>
    </view>

    <view v-else class="list">
      <view
        v-for="msg in messages"
        :key="msg.id"
        class="msg-card"
        :class="{ notify: msg.msg_type === 'egg_match_notify' }"
      >
        <view class="msg-head">
          <text class="msg-tag">
            {{ msg.msg_type === 'egg_match_notify' ? '🥚 换蛋匹配' : '💬 私聊' }}
          </text>
          <text class="msg-time">{{ formatTime(msg.created_at) }}</text>
        </view>
        <text class="msg-content">{{ msg.content }}</text>

        <view v-if="msg.msg_type === 'egg_match_notify' && msg.payload" class="notify-extra">
          <text class="notify-line">对方游戏ID：{{ msg.payload.partner_game_id || '未填写' }}</text>
          <view
            v-if="msg.payload.partner_game_id"
            class="copy-btn"
            @tap="copyGameId(msg.payload.partner_game_id)"
          >
            <text>复制游戏ID</text>
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

.list { display: flex; flex-direction: column; gap: 18rpx; }

.msg-card {
  padding: 24rpx;
  border-radius: 24rpx;
  background: #ffffff;
  box-shadow: 0 8rpx 24rpx rgba(64, 125, 255, 0.06);
}
.msg-card.notify { background: linear-gradient(135deg, #f6f0ff 0%, #f0f6ff 100%); }

.msg-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}
.msg-tag { font-size: 24rpx; font-weight: 700; color: #6c63ff; }
.msg-time { font-size: 22rpx; color: #9fb1cf; }
.msg-content { font-size: 28rpx; line-height: 1.6; color: #1f3760; }

.notify-extra {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16rpx;
  padding-top: 16rpx;
  border-top: 2rpx solid rgba(108, 99, 255, 0.12);
}
.notify-line { font-size: 24rpx; color: #5a76a8; }
.copy-btn {
  padding: 10rpx 26rpx;
  border-radius: 999rpx;
  background: #6c63ff;
}
.copy-btn text { font-size: 22rpx; color: #ffffff; font-weight: 700; }
</style>
