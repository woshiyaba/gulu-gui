const SHARE_TITLE = '洛克王国精灵图鉴 - 精灵、技能、地图一站查询'
const SHARE_IMAGE_URL = '/static/logo.png'
const HOME_PATH = 'pages/index/index'

type SharePage = {
  route?: string
  options?: Record<string, string | number | boolean | null | undefined>
}

function buildQuery(options: SharePage['options'] = {}) {
  const query = Object.entries(options)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)

  return query.join('&')
}

function getCurrentShareInfo() {
  const pages = getCurrentPages() as SharePage[]
  const currentPage = pages[pages.length - 1]
  const route = currentPage?.route || HOME_PATH
  const query = buildQuery(currentPage?.options)

  return {
    path: query ? `${route}?${query}` : route,
    query,
  }
}

export default {
  onShareAppMessage() {
    return {
      title: SHARE_TITLE,
      path: getCurrentShareInfo().path,
      imageUrl: SHARE_IMAGE_URL,
    }
  },

  onShareTimeline() {
    // 朋友圈分享不能指定 path，只能沿用当前页面并透传 query。
    return {
      title: SHARE_TITLE,
      query: getCurrentShareInfo().query,
      imageUrl: SHARE_IMAGE_URL,
    }
  },
}
