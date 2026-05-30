<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import { fetchPetAvatar } from '@/api/pokemon'
import { getStoredUserId, silentLogin } from '@/utils/auth'
import { connectPetChatStream, type PetChatConnection } from '@/utils/ws'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

const petId = ref('')
const petName = ref('宠物')
const avatar = ref('')
const messages = ref<ChatMessage[]>([])
const draft = ref('')
const connected = ref(false)
const sending = ref(false)
const errorTip = ref('')
const scrollTop = ref(0)

// 自定义导航栏需要避让状态栏
const statusBarHeight = uni.getSystemInfoSync().statusBarHeight || 0

let conn: PetChatConnection | null = null
// 当前正在流式接收的宠物气泡下标；-1 表示没有
let streamingIndex = -1

function goBack() {
  if (getCurrentPages().length > 1) {
    uni.navigateBack()
    return
  }
  uni.reLaunch({ url: '/pages/index/index' })
}

function scrollToBottom() {
  nextTick(() => {
    // 在两个足够大的值之间切换，保证 scroll-top 每次都变化以触发滚动
    scrollTop.value = scrollTop.value === 1_000_000 ? 1_000_001 : 1_000_000
  })
}

function handleHistory(history: { role: string; content: string }[]) {
  messages.value = history
    .filter((m) => m.content)
    .map((m) => ({
      role: m.role === 'user' ? 'user' : 'assistant',
      content: m.content,
    }))
  scrollToBottom()
}

function handleStart() {
  messages.value.push({ role: 'assistant', content: '' })
  streamingIndex = messages.value.length - 1
  scrollToBottom()
}

function handleChunk(chunk: string) {
  if (streamingIndex < 0) {
    handleStart()
  }
  messages.value[streamingIndex].content += chunk
  scrollToBottom()
}

function handleEnd() {
  // 宠物没说出任何内容时移除空气泡
  if (streamingIndex >= 0 && !messages.value[streamingIndex].content) {
    messages.value.splice(streamingIndex, 1)
  }
  streamingIndex = -1
  sending.value = false
}

function handleError(message: string) {
  // 丢弃空的流式气泡，把错误作为一条宠物消息提示出来
  if (streamingIndex >= 0 && !messages.value[streamingIndex].content) {
    messages.value.splice(streamingIndex, 1)
  }
  streamingIndex = -1
  sending.value = false
  errorTip.value = message
  uni.showToast({ title: message, icon: 'none' })
}

async function setupConnection() {
  let userId = getStoredUserId()
  if (!userId) {
    await silentLogin()
    userId = getStoredUserId()
  }
  if (!userId) {
    errorTip.value = '请先登录后再聊天'
    return
  }

  conn = connectPetChatStream(userId, petId.value, {
    onHistory: handleHistory,
    onStart: handleStart,
    onChunk: handleChunk,
    onEnd: handleEnd,
    onError: handleError,
    onOpen: () => {
      connected.value = true
      errorTip.value = ''
    },
    onClose: () => {
      connected.value = false
    },
  })

  try {
    await conn.whenOpen
  } catch (err) {
    errorTip.value = err instanceof Error ? err.message : '连接失败'
  }
}

function sendMessage() {
  const text = draft.value.trim()
  if (!text || !conn || !connected.value || sending.value) return

  messages.value.push({ role: 'user', content: text })
  conn.send(text)
  draft.value = ''
  sending.value = true
  errorTip.value = ''
  scrollToBottom()
}

onLoad((options) => {
  petId.value = typeof options?.pet_id === 'string' ? options.pet_id : ''
  const rawName = typeof options?.name === 'string' ? options.name : ''
  if (rawName) {
    petName.value = decodeURIComponent(rawName)
    uni.setNavigationBarTitle({ title: petName.value })
  }

  if (!petId.value) {
    errorTip.value = '缺少宠物信息，无法开始聊天'
    return
  }

  fetchPetAvatar(Number(petId.value))
    .then((res) => {
      avatar.value = res.avatar || ''
    })
    .catch(() => {
      /* 头像拉取失败用占位符兜底 */
    })

  void setupConnection()
})

onUnload(() => {
  conn?.close()
  conn = null
})
</script>

<template>
  <view class="chat-page">
    <view class="nav-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="nav-row">
        <view class="nav-back" @tap="goBack">
          <text class="nav-back-icon">‹</text>
        </view>
        <text class="nav-status" :class="{ 'nav-status--on': connected }">
          {{ connected ? '在线' : '连接中…' }}
        </text>
        <text class="nav-title">{{ petName }}</text>
      </view>
    </view>

    <scroll-view
      class="msg-scroll"
      scroll-y
      :scroll-top="scrollTop"
      :scroll-with-animation="true"
    >
      <view class="msg-list">
        <view
          v-for="(msg, index) in messages"
          :key="index"
          class="msg-row"
          :class="msg.role === 'user' ? 'msg-row--user' : 'msg-row--pet'"
        >
          <template v-if="msg.role === 'assistant'">
            <view class="msg-avatar">
              <image
                v-if="avatar"
                class="msg-avatar-img"
                :src="avatar"
                mode="aspectFit"
              />
              <text v-else class="msg-avatar-placeholder">{{ petName.slice(0, 1) }}</text>
            </view>
            <view class="bubble bubble--pet">
              <text class="bubble-text">{{ msg.content || '…' }}</text>
            </view>
          </template>
          <template v-else>
            <view class="bubble bubble--user">
              <text class="bubble-text">{{ msg.content }}</text>
            </view>
          </template>
        </view>

        <view v-if="!messages.length" class="empty-tip">
          <text>和 {{ petName }} 打个招呼吧～</text>
        </view>
      </view>
    </scroll-view>

    <view class="input-bar">
      <input
        v-model="draft"
        class="input-box"
        type="text"
        confirm-type="send"
        placeholder="说点什么…"
        :adjust-position="true"
        @confirm="sendMessage"
      />
      <view
        class="send-btn"
        :class="{ 'send-btn--disabled': !draft.trim() || !connected || sending }"
        @tap="sendMessage"
      >
        <text>发送</text>
      </view>
    </view>
  </view>
</template>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(180deg, #f4f8ff 0%, #eef4ff 100%);
}

.nav-bar {
  background: transparent;
}

.nav-row {
  position: relative;
  display: flex;
  align-items: center;
  height: 88rpx;
  padding: 0 16rpx;
}

.nav-back {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56rpx;
  height: 56rpx;
}

.nav-back-icon {
  font-size: 56rpx;
  line-height: 1;
  color: #1f3760;
}

.nav-status {
  margin-left: 8rpx;
  font-size: 24rpx;
  color: #b0bdd6;
}

.nav-status--on {
  color: #35c88a;
}

.nav-title {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  max-width: 50%;
  font-size: 40rpx;
  font-weight: 800;
  color: #1f3760;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.msg-scroll {
  flex: 1;
  min-height: 0;
}

.msg-list {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
  padding: 28rpx 24rpx;
}

.msg-row {
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
}

.msg-row--pet {
  justify-content: flex-start;
}

.msg-row--user {
  justify-content: flex-end;
}

.msg-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 72rpx;
  height: 72rpx;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 4rpx 12rpx rgba(64, 125, 255, 0.12);
  overflow: hidden;
}

.msg-avatar-img {
  width: 100%;
  height: 100%;
}

.msg-avatar-placeholder {
  font-size: 30rpx;
  font-weight: 700;
  color: #7eaef8;
}

.bubble {
  max-width: 70%;
  padding: 18rpx 22rpx;
  border-radius: 22rpx;
  font-size: 28rpx;
  line-height: 1.6;
  word-break: break-word;
}

.bubble--pet {
  background: #ffffff;
  color: #2a3d5c;
  border-top-left-radius: 6rpx;
  box-shadow: 0 6rpx 18rpx rgba(64, 125, 255, 0.08);
}

.bubble--user {
  background: linear-gradient(135deg, #2b74ff 0%, #5b9aff 100%);
  color: #ffffff;
  border-top-right-radius: 6rpx;
  box-shadow: 0 6rpx 18rpx rgba(43, 116, 255, 0.24);
}

.bubble-text {
  white-space: pre-wrap;
}

.empty-tip {
  margin-top: 120rpx;
  text-align: center;
  font-size: 26rpx;
  color: #9fb1d0;
}

.input-bar {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 16rpx 24rpx;
  padding-bottom: calc(16rpx + constant(safe-area-inset-bottom));
  padding-bottom: calc(16rpx + env(safe-area-inset-bottom));
  background: #ffffff;
  box-shadow: 0 -4rpx 16rpx rgba(64, 125, 255, 0.06);
}

.input-box {
  flex: 1;
  height: 76rpx;
  padding: 0 26rpx;
  border-radius: 999rpx;
  background: #f1f5ff;
  font-size: 28rpx;
  color: #1f3760;
}

.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 120rpx;
  height: 76rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #2b74ff 0%, #5b9aff 100%);
  color: #ffffff;
  font-size: 28rpx;
  font-weight: 600;
}

.send-btn--disabled {
  opacity: 0.5;
}
</style>
