<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  ANNOUNCEMENT_IMAGE_URL,
  ANNOUNCEMENT_TEXT,
  ANNOUNCEMENT_TITLE,
} from '@/data/announcement'
import {
  fetchAnnouncementLikeCount,
  hasLikedAnnouncementLocally,
  likeAnnouncement,
  markAnnouncementLikedLocally,
} from '@/api/announcement'

const startupModalVisible = ref(true)
const likeCount = ref(0)
const likedLocally = ref(hasLikedAnnouncementLocally())
const liking = ref(false)
const likeError = ref('')

function closeStartupModal() {
  startupModalVisible.value = false
}

async function loadLikeCount() {
  try {
    likeCount.value = await fetchAnnouncementLikeCount()
  } catch {
    likeError.value = '点赞数加载失败'
  }
}

async function handleLike() {
  if (likedLocally.value || liking.value) return
  liking.value = true
  likeError.value = ''
  try {
    likeCount.value = await likeAnnouncement()
    likedLocally.value = true
    markAnnouncementLikedLocally()
  } catch {
    likeError.value = '点赞失败，请稍后重试'
  } finally {
    liking.value = false
  }
}

onMounted(() => {
  void loadLikeCount()
})
</script>

<template>
  <RouterView />

  <Teleport to="body">
    <div
      v-if="startupModalVisible"
      class="startup-modal-mask"
      role="dialog"
      aria-modal="true"
      aria-labelledby="startup-modal-title"
      @click.self="closeStartupModal"
    >
      <section class="startup-modal" @click.stop>
        <header class="startup-modal-header">
          <h2 id="startup-modal-title" class="startup-modal-title">{{ ANNOUNCEMENT_TITLE }}</h2>
          <button
            type="button"
            class="startup-modal-close"
            aria-label="关闭"
            @click="closeStartupModal"
          >
            ✕
          </button>
        </header>
        <div class="startup-modal-body">
          <p class="startup-modal-text">{{ ANNOUNCEMENT_TEXT }}</p>
          <img
            class="startup-modal-image"
            :src="ANNOUNCEMENT_IMAGE_URL"
            alt="公告配图"
            loading="lazy"
          />
        </div>
        <footer class="startup-modal-footer">
          <div class="startup-modal-footer-left">
            <button
              type="button"
              class="startup-like-btn"
              :class="{ 'is-liked': likedLocally }"
              :disabled="likedLocally || liking"
              @click="handleLike"
            >
              <span class="startup-like-icon" aria-hidden="true">👍</span>
              <span>{{ likedLocally ? '已点赞' : liking ? '点赞中…' : '点赞' }}</span>
              <span class="startup-like-count">{{ likeCount }}</span>
            </button>
            <p v-if="likeError" class="startup-like-error">{{ likeError }}</p>
          </div>
          <button type="button" class="startup-modal-btn" @click="closeStartupModal">知道了</button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.startup-modal-mask {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(2px);
}

.startup-modal {
  width: min(520px, 100%);
  max-height: min(85vh, 720px);
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 14px;
  box-shadow: var(--color-shadow);
  overflow: hidden;
}

.startup-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--color-border);
}

.startup-modal-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
}

.startup-modal-close {
  border: none;
  background: transparent;
  color: var(--color-muted);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
}

.startup-modal-close:hover {
  color: var(--color-text);
  background: var(--color-hover);
}

.startup-modal-body {
  flex: 1;
  min-height: 80px;
  padding: 18px;
  color: var(--color-text);
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.startup-modal-text {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.startup-modal-image {
  width: 100%;
  height: auto;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background: var(--color-img-bg);
}

.startup-modal-footer {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 18px 16px;
  border-top: 1px solid var(--color-border);
}

.startup-modal-footer-left {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  min-width: 0;
}

.startup-like-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 13px;
  color: var(--color-text);
  background: var(--color-surface);
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.startup-like-btn:hover:not(:disabled) {
  background: var(--color-hover);
  border-color: var(--color-accent);
}

.startup-like-btn:disabled {
  cursor: default;
  opacity: 0.85;
}

.startup-like-btn.is-liked {
  color: var(--color-accent);
  border-color: var(--color-accent);
  background: var(--color-tag-bg);
}

.startup-like-icon {
  font-size: 15px;
  line-height: 1;
}

.startup-like-count {
  font-weight: 600;
  color: var(--color-muted);
}

.startup-like-btn.is-liked .startup-like-count {
  color: var(--color-accent);
}

.startup-like-error {
  margin: 0;
  font-size: 12px;
  color: #dc2626;
}

.startup-modal-btn {
  flex-shrink: 0;
  border: none;
  border-radius: 8px;
  padding: 8px 18px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  background: var(--color-accent);
  cursor: pointer;
}

.startup-modal-btn:hover {
  filter: brightness(1.05);
}
</style>
