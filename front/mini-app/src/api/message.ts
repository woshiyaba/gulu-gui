import { request } from '@/utils/request'
import { getStoredUserId } from '@/utils/auth'

export type MessageType = 'chat' | 'egg_match_notify' | string

export interface UserMessage {
  id: number
  from_user_id: number
  to_user_id: number
  msg_type: MessageType
  content: string
  payload: Record<string, any> | null
  is_delivered: boolean
  delivered_at: string | null
  is_read: boolean
  created_at: string | null
}

/** 收件箱：我收到的消息 / 通知（按时间倒序）。 */
export function fetchInbox(userId: number | string, limit = 50) {
  return request<UserMessage[]>({
    url: '/api/messages/inbox',
    data: { user_id: userId, limit },
  })
}

/** 未读消息数（用于红点）。 */
export function fetchUnreadCount(userId: number | string) {
  return request<{ count: number }>({
    url: '/api/messages/unread-count',
    data: { user_id: userId },
  })
}

/** 发送一条私聊消息（REST 兜底，实时走 ws）。 */
export function sendMessage(fromUserId: number | string, toUserId: number | string, content: string) {
  return request<UserMessage>({
    url: '/api/messages',
    method: 'POST',
    data: { from_user_id: fromUserId, to_user_id: toUserId, content },
  })
}

/** 标记若干消息为已读。 */
export function markMessagesRead(toUserId: number | string, ids: number[]) {
  return request<{ ok: boolean }>({
    url: '/api/messages/read',
    method: 'POST',
    data: { to_user_id: toUserId, ids },
  })
}

/** 拉取两个用户间的历史会话。 */
export function fetchConversation(userA: number | string, userB: number | string, limit = 50) {
  return request<UserMessage[]>({
    url: '/api/messages/conversation',
    data: { user_a: userA, user_b: userB, limit },
  })
}

/**
 * 刷新「更多」tab 的红点：未读 > 0 显示，否则隐藏。index 3 = 底部「更多」按钮。
 * 未登录时静默跳过。
 */
export async function refreshMoreTabRedDot(): Promise<number> {
  const userId = getStoredUserId()
  if (!userId) return 0
  try {
    const { count } = await fetchUnreadCount(userId)
    if (count > 0) {
      uni.showTabBarRedDot({ index: 3 })
    } else {
      uni.hideTabBarRedDot({ index: 3 })
    }
    return count
  } catch {
    return 0
  }
}
