import { request } from '@/utils/request'

export interface FeedbackCreatePayload {
  content: string
  contact?: string
  feedback_type?: string
}

export interface FeedbackItem {
  id: number
  user_id: number | null
  content: string
  contact: string | null
  feedback_type: string | null
  status: string
  created_at: string | null
  updated_at: string | null
}

/** 提交用户反馈（自动携带登录用户 id，匿名也可提交）。 */
export function submitFeedback(payload: FeedbackCreatePayload) {
  return request<FeedbackItem>({
    url: '/api/feedback',
    method: 'POST',
    data: payload,
  })
}
