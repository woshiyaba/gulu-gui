<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchAnnouncement } from '@/api/pokemon'
import type { Announcement } from '@/types'

// 本会话内已看过的版本（避免同会话内反复弹出）
const SEEN_KEY = 'roco_announce_seen'
// 「今日不再提示」记录：{ v: 版本, exp: 过期时间戳(ms) }
const DISMISS_KEY = 'roco_announce_dismiss'

const visible = ref(false)
const announcement = ref<Announcement | null>(null)
const dontShowToday = ref(false)

// 公告更新时间作为版本号；后台改动后版本变化，已关闭的公告会重新弹出。
function versionOf(a: Announcement): string {
  return a.updated_at || `${a.title}|${a.content}`
}

function endOfTodayMs(): number {
  const d = new Date()
  d.setHours(23, 59, 59, 999)
  return d.getTime()
}

function readDismiss(): { v: string; exp: number } | null {
  try {
    const raw = localStorage.getItem(DISMISS_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function shouldShow(a: Announcement): boolean {
  const v = versionOf(a)
  if (sessionStorage.getItem(SEEN_KEY) === v) return false
  const dismiss = readDismiss()
  if (dismiss && dismiss.v === v && Date.now() < dismiss.exp) return false
  return true
}

async function load() {
  try {
    const a = await fetchAnnouncement()
    if (!a || (!a.title && !a.content)) return
    announcement.value = a
    if (shouldShow(a)) visible.value = true
  } catch {
    // 公告拉取失败不影响主页其余功能
  }
}

function close() {
  const a = announcement.value
  if (a) {
    const v = versionOf(a)
    // 本会话标记已读，避免在首页间来回切换时反复弹窗
    sessionStorage.setItem(SEEN_KEY, v)
    if (dontShowToday.value) {
      localStorage.setItem(DISMISS_KEY, JSON.stringify({ v, exp: endOfTodayMs() }))
    }
  }
  visible.value = false
}

onMounted(load)
</script>

<template>
  <div v-if="visible && announcement" class="announce-mask" @click.self="close">
    <section class="announce-card" role="dialog" aria-modal="true">
      <header class="announce-header">
        <h3 class="announce-title">
          <span class="announce-icon">📢</span>
          {{ announcement.title || '公告' }}
        </h3>
        <button type="button" class="announce-close" aria-label="关闭" @click="close">✕</button>
      </header>

      <div class="announce-body">{{ announcement.content }}</div>

      <footer class="announce-footer">
        <label class="announce-skip">
          <input v-model="dontShowToday" type="checkbox" />
          今日不再提示
        </label>
        <button type="button" class="announce-btn" @click="close">我知道了</button>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.announce-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 1000;
}

.announce-card {
  width: min(100%, 480px);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.28);
  overflow: hidden;
}

.announce-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
}

.announce-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: var(--color-accent);
}

.announce-icon {
  font-size: 18px;
}

.announce-close {
  border: none;
  background: transparent;
  color: var(--color-muted);
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  transition: color 0.2s, background-color 0.2s;
}

.announce-close:hover {
  color: var(--color-text);
  background: var(--color-hover);
}

.announce-body {
  padding: 18px 20px;
  overflow-y: auto;
  color: var(--color-text);
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.announce-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 20px;
  border-top: 1px solid var(--color-border);
}

.announce-skip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--color-muted);
  cursor: pointer;
}

.announce-skip input {
  margin: 0;
  cursor: pointer;
}

.announce-btn {
  padding: 8px 20px;
  border: 1px solid transparent;
  border-radius: 20px;
  background: var(--color-accent);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.announce-btn:hover {
  opacity: 0.9;
}
</style>
