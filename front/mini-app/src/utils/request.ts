interface RequestOptions {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: unknown
  timeout?: number
}

interface ApiErrorPayload {
  detail?: string
  message?: string
}

const DEFAULT_API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://wikiroco.com'
const API_BASE_URL = DEFAULT_API_BASE_URL.replace(/\/+$/, '')
const DEFAULT_REQUEST_TIMEOUT = 5 * 60 * 1000

function isOmittableQueryValue(value: unknown): boolean {
  if (value === undefined || value === null) return true
  if (typeof value === 'string') {
    const t = value.trim()
    // 避免 URL 里出现 name=undefined（常见于把 undefined 当成字符串拼接）
    if (t === '' || t === 'undefined' || t === 'null') return true
  }
  return false
}

function normalizeRequestData(data: unknown) {
  if (!data || Array.isArray(data) || typeof data !== 'object') {
    return data as any
  }

  // 统一过滤空查询参数，避免把 name=undefined 这类值拼到 URL 上。
  return Object.fromEntries(
    Object.entries(data as Record<string, unknown>).filter(([, value]) => !isOmittableQueryValue(value)),
  ) as any
}

export function request<T>({ url, method = 'GET', data, timeout = DEFAULT_REQUEST_TIMEOUT }: RequestOptions): Promise<T> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${API_BASE_URL}${url}`,
      method,
      data: normalizeRequestData(data),
      timeout,
      success: (response) => {
        const { statusCode, data: body } = response
        if (statusCode >= 200 && statusCode < 300) {
          resolve(body as T)
          return
        }

        const payload = (body || {}) as ApiErrorPayload
        reject(new Error(payload.detail || payload.message || `请求失败（${statusCode}）`))
      },
      fail: (error) => {
        reject(new Error(error.errMsg || '网络请求失败'))
      },
    })
  })
}
