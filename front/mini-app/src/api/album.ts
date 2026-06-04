import { request } from '@/utils/request'
import { getStoredUserId } from '@/utils/auth'

const DEFAULT_API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://wikiroco.com'
const API_BASE_URL = DEFAULT_API_BASE_URL.replace(/\/+$/, '')

export interface AlbumPhoto {
  id: number
  user_id: number
  pet_id: number
  image_url: string
  is_featured: boolean
  created_at: string | null
  updated_at: string | null
}

export interface AlbumCreatePayload {
  user_id: number
  pet_id: number
  image_url: string
  is_featured?: boolean
}

/** 查询某用户某宠物的相册（精选优先，后端已排序）。 */
export function fetchAlbumPhotos(userId: number | string, petId: number) {
  return request<AlbumPhoto[]>({
    url: '/api/album',
    data: { user_id: userId, pet_id: petId },
  })
}

/** 新增一张相册照片。 */
export function createAlbumPhoto(payload: AlbumCreatePayload) {
  return request<AlbumPhoto>({
    url: '/api/album',
    method: 'POST',
    data: payload,
  })
}

/** 设置 / 取消精选。 */
export function setAlbumPhotoFeatured(photoId: number, isFeatured: boolean) {
  return request<AlbumPhoto>({
    url: `/api/album/${photoId}/featured`,
    method: 'POST',
    data: { is_featured: isFeatured },
  })
}

/** 删除一张照片（后端会同步删除 OSS 对象）。 */
export function deleteAlbumPhoto(photoId: number) {
  return request<AlbumPhoto>({
    url: `/api/album/${photoId}`,
    method: 'DELETE',
  })
}

/** 上传本地图片到 OSS，返回访问 URL。走 uni.uploadFile（multipart）。 */
export function uploadAlbumImage(filePath: string): Promise<string> {
  const userId = getStoredUserId()
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${API_BASE_URL}/api/file/upload`,
      filePath,
      name: 'file',
      formData: { prefix: 'album' },
      header: userId ? { Authorization: userId } : undefined,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            const body = JSON.parse(res.data) as { url?: string }
            if (body.url) {
              resolve(body.url)
              return
            }
            reject(new Error('上传响应缺少 url'))
          } catch {
            reject(new Error('上传响应解析失败'))
          }
          return
        }
        reject(new Error(`上传失败（${res.statusCode}）`))
      },
      fail: (err) => reject(new Error(err.errMsg || '上传失败')),
    })
  })
}
