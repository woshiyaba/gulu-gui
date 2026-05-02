const DEFAULT_API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://wikiroco.com'
const API_BASE_URL = DEFAULT_API_BASE_URL.replace(/\/+$/, '')
const USER_ID_STORAGE_KEY = 'wx_user_id'
const LOGIN_TIMEOUT = 15000

interface WxLoginResponse {
  user_id: number
  social_member_id?: number
  openid?: string
  session_key?: string
  unionid?: string
  is_new_user?: boolean
}

function setStoredUserId(userId: number) {
  if (!userId) return
  uni.setStorageSync(USER_ID_STORAGE_KEY, String(userId))
}

export function getStoredUserId(): string {
  try {
    return String(uni.getStorageSync(USER_ID_STORAGE_KEY) || '').trim()
  } catch {
    return ''
  }
}

function loginWithWxCode(): Promise<string> {
  return new Promise((resolve, reject) => {
    uni.login({
      provider: 'weixin',
      success: (result) => {
        if (result.code) {
          resolve(result.code)
          return
        }
        reject(new Error('wx.login did not return code'))
      },
      fail: (error) => {
        reject(new Error(error.errMsg || 'wx.login failed'))
      },
    })
  })
}

function requestSilentLogin(code: string): Promise<WxLoginResponse> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${API_BASE_URL}/api/wx/login`,
      method: 'POST',
      data: { code },
      timeout: LOGIN_TIMEOUT,
      success: (response) => {
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(response.data as WxLoginResponse)
          return
        }
        reject(new Error(`silent login failed: ${response.statusCode}`))
      },
      fail: (error) => {
        reject(new Error(error.errMsg || 'silent login request failed'))
      },
    })
  })
}

export async function silentLogin(): Promise<void> {
  try {
    const code = await loginWithWxCode()
    const result = await requestSilentLogin(code)
    setStoredUserId(Number(result.user_id || 0))
  } catch (error) {
    console.warn('[auth] silent login skipped', error)
  }
}
