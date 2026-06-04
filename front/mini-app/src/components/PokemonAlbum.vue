<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  fetchAlbumPhotos,
  createAlbumPhoto,
  setAlbumPhotoFeatured,
  deleteAlbumPhoto,
  uploadAlbumImage,
  type AlbumPhoto,
} from '@/api/album'
import { getStoredUserId } from '@/utils/auth'

const props = defineProps<{
  petId: number
  petName: string
  /** 当前是否处于相册 Tab：用于首次切入时懒加载 */
  active: boolean
}>()

const MAX_ALBUM_PHOTOS = 9
const photos = ref<AlbumPhoto[]>([])
const loading = ref(false)
const loaded = ref(false)
const error = ref('')
const uploading = ref(false)

// 精选优先（后端已排序，这里兜底再排一次）
const sortedPhotos = computed(() =>
  [...photos.value].sort((a, b) => Number(b.is_featured) - Number(a.is_featured)),
)
const canUploadMore = computed(() => photos.value.length < MAX_ALBUM_PHOTOS)
// 3*3 宫格：剩余空位用线框加号占位
const emptySlots = computed(() => Math.max(0, MAX_ALBUM_PHOTOS - photos.value.length))

async function load() {
  const userId = getStoredUserId()
  if (!userId) {
    error.value = '请先登录后再查看相册'
    photos.value = []
    loaded.value = true
    return
  }

  loading.value = true
  error.value = ''
  try {
    photos.value = await fetchAlbumPhotos(userId, props.petId)
    loaded.value = true
  } catch (err) {
    error.value = err instanceof Error ? err.message : '相册加载失败'
  } finally {
    loading.value = false
  }
}

// 首次切入相册 Tab 时懒加载
watch(
  () => props.active,
  (val) => {
    if (val && !loaded.value && !loading.value) void load()
  },
  { immediate: true },
)

// 切换宠物时重置；若当前正展示相册则立即重新加载
watch(
  () => props.petId,
  () => {
    photos.value = []
    loaded.value = false
    error.value = ''
    if (props.active) void load()
  },
)

function chooseImageFile(): Promise<string> {
  return new Promise((resolve, reject) => {
    uni.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const path = (res.tempFilePaths && res.tempFilePaths[0]) || ''
        if (path) resolve(path)
        else reject(new Error('未选择图片'))
      },
      fail: () => reject(new Error('已取消')),
    })
  })
}

async function uploadPhoto() {
  if (uploading.value) return
  const userId = getStoredUserId()
  if (!userId) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    return
  }
  if (!canUploadMore.value) {
    uni.showToast({ title: `最多上传 ${MAX_ALBUM_PHOTOS} 张`, icon: 'none' })
    return
  }

  let filePath = ''
  try {
    filePath = await chooseImageFile()
  } catch {
    return // 用户取消，不提示
  }

  uploading.value = true
  uni.showLoading({ title: '上传中...' })
  try {
    const url = await uploadAlbumImage(filePath)
    const photo = await createAlbumPhoto({
      user_id: Number(userId),
      pet_id: props.petId,
      image_url: url,
    })
    photos.value.push(photo)
    uni.showToast({ title: '上传成功', icon: 'success' })
  } catch (err) {
    uni.showToast({ title: err instanceof Error ? err.message : '上传失败', icon: 'none' })
  } finally {
    uploading.value = false
    uni.hideLoading()
  }
}

async function toggleFeatured(photo: AlbumPhoto) {
  try {
    const updated = await setAlbumPhotoFeatured(photo.id, !photo.is_featured)
    const idx = photos.value.findIndex((p) => p.id === photo.id)
    if (idx >= 0) photos.value[idx] = updated
  } catch (err) {
    uni.showToast({ title: err instanceof Error ? err.message : '操作失败', icon: 'none' })
  }
}

function deletePhoto(photo: AlbumPhoto) {
  uni.showModal({
    title: '删除照片',
    content: '确定删除这张照片吗？',
    success: async (res) => {
      if (!res.confirm) return
      try {
        await deleteAlbumPhoto(photo.id)
        photos.value = photos.value.filter((p) => p.id !== photo.id)
        uni.showToast({ title: '已删除', icon: 'success' })
      } catch (err) {
        uni.showToast({ title: err instanceof Error ? err.message : '删除失败', icon: 'none' })
      }
    },
  })
}

// 重新上传：先选新图，再删除旧图（含 OSS 对象），最后上传新图
async function reuploadPhoto(photo: AlbumPhoto) {
  if (uploading.value) return
  const userId = getStoredUserId()
  if (!userId) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    return
  }

  let filePath = ''
  try {
    filePath = await chooseImageFile()
  } catch {
    return
  }

  uploading.value = true
  uni.showLoading({ title: '更新中...' })
  try {
    await deleteAlbumPhoto(photo.id)
    photos.value = photos.value.filter((p) => p.id !== photo.id)
    const url = await uploadAlbumImage(filePath)
    const created = await createAlbumPhoto({
      user_id: Number(userId),
      pet_id: props.petId,
      image_url: url,
      is_featured: photo.is_featured,
    })
    photos.value.push(created)
    uni.showToast({ title: '已更新', icon: 'success' })
  } catch (err) {
    uni.showToast({ title: err instanceof Error ? err.message : '操作失败', icon: 'none' })
  } finally {
    uploading.value = false
    uni.hideLoading()
  }
}

function previewImage(photo: AlbumPhoto) {
  uni.previewImage({
    urls: sortedPhotos.value.map((p) => p.image_url),
    current: photo.image_url,
  })
}

// 长按已上传的照片，弹出管理菜单：精选 / 重传 / 删除
function managePhoto(photo: AlbumPhoto) {
  uni.showActionSheet({
    itemList: [photo.is_featured ? '取消精选' : '设为精选', '重新上传', '删除'],
    success: (res) => {
      if (res.tapIndex === 0) void toggleFeatured(photo)
      else if (res.tapIndex === 1) void reuploadPhoto(photo)
      else if (res.tapIndex === 2) deletePhoto(photo)
    },
  })
}
</script>

<template>
  <view class="section-card">
    <view class="album-head">
      <text class="section-title">精灵相册</text>
      <text class="album-count">{{ photos.length }}/{{ MAX_ALBUM_PHOTOS }}</text>
    </view>
    <text class="album-tip">记录你和 {{ petName }} 的合影，精选照片永远展示在最前方。</text>

    <view v-if="loading" class="album-state">
      <text class="empty-text">加载中...</text>
    </view>
    <view v-else-if="error" class="album-state">
      <text class="empty-text">{{ error }}</text>
    </view>
    <view v-else class="album-grid">
      <view
        v-for="photo in sortedPhotos"
        :key="photo.id"
        class="album-cell"
        @tap="previewImage(photo)"
        @longpress="managePhoto(photo)"
      >
        <view class="album-cell-inner">
          <image class="album-img" :src="photo.image_url" mode="aspectFill" />
          <text v-if="photo.is_featured" class="album-featured-badge">精选</text>
        </view>
      </view>

      <view
        v-for="n in emptySlots"
        :key="'empty-' + n"
        class="album-cell"
        @tap="uploadPhoto"
      >
        <view class="album-cell-inner album-cell-inner--empty">
          <text class="album-upload-plus">＋</text>
        </view>
      </view>
    </view>
    <text v-if="!loading && !error" class="album-manage-tip">长按照片可设为精选 / 重传 / 删除</text>
  </view>
</template>

<style scoped>
.section-card {
  padding: 28rpx;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 12rpx 32rpx rgba(64, 125, 255, 0.08);
}

.section-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #214887;
}

.empty-text {
  display: block;
  margin-top: 14rpx;
  font-size: 24rpx;
  line-height: 1.8;
  color: #6f89b2;
}

.album-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.album-count {
  font-size: 24rpx;
  color: #7b8aa6;
}

.album-tip {
  display: block;
  margin: 8rpx 0 20rpx;
  font-size: 24rpx;
  color: #8a99b5;
  line-height: 1.6;
}

.album-state {
  padding: 48rpx 0;
  text-align: center;
}

.album-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}

/* 3 列宫格：每格宽度 = (100% - 2 个间距) / 3 */
.album-cell {
  position: relative;
  width: calc((100% - 32rpx) / 3);
}

/* 用 padding-bottom 撑出正方形，内部内容绝对定位铺满 */
.album-cell::after {
  display: block;
  padding-bottom: 100%;
  content: '';
}

.album-cell-inner {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  border-radius: 16rpx;
  overflow: hidden;
  background: #eef3fb;
}

.album-img {
  width: 100%;
  height: 100%;
}

.album-featured-badge {
  position: absolute;
  top: 10rpx;
  left: 10rpx;
  padding: 2rpx 14rpx;
  border-radius: 999rpx;
  background: linear-gradient(90deg, #ff9d3c 0%, #ffba6b 100%);
  color: #ffffff;
  font-size: 20rpx;
}

.album-cell-inner--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2rpx dashed #b9cdf2;
  background: #f6faff;
}

.album-upload-plus {
  font-size: 56rpx;
  line-height: 1;
  color: #7eaef8;
}

.album-manage-tip {
  display: block;
  margin-top: 20rpx;
  font-size: 22rpx;
  color: #a3b0c6;
  text-align: center;
}
</style>
