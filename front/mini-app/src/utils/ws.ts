const DEFAULT_API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://wikiroco.com'
const API_BASE_URL = DEFAULT_API_BASE_URL.replace(/\/+$/, '')

function toWsBase(http: string): string {
  if (/^https:/i.test(http)) return http.replace(/^https:/i, 'wss:')
  if (/^http:/i.test(http)) return http.replace(/^http:/i, 'ws:')
  return http
}

const WS_BASE_URL = toWsBase(API_BASE_URL)

export interface PkStreamEvent {
  task_id?: string
  node?: string
  status: 'start' | 'streaming' | 'end' | 'done' | 'error' | string
  chunk?: string
  message?: string
  result?: unknown
}

export interface PkStreamHandlers {
  onStart?: (event: PkStreamEvent) => void
  onChunk?: (chunk: string, event: PkStreamEvent) => void
  onEnd?: (event: PkStreamEvent) => void
  onDone?: (result: unknown, event: PkStreamEvent) => void
  onError?: (message: string, event: PkStreamEvent) => void
  onOpen?: () => void
  onClose?: () => void
}

export interface PkStreamConnection {
  task: UniApp.SocketTask
  whenOpen: Promise<void>
  close: () => void
}

export function connectPkStream(userId: string, handlers: PkStreamHandlers): PkStreamConnection {
  const url = `${WS_BASE_URL}/ws/${encodeURIComponent(userId)}`

  let resolveOpen: (() => void) | null = null
  let rejectOpen: ((err: Error) => void) | null = null
  let opened = false

  const whenOpen = new Promise<void>((resolve, reject) => {
    resolveOpen = resolve
    rejectOpen = reject
  })

  const task = uni.connectSocket({
    url,
    complete: () => {},
  }) as unknown as UniApp.SocketTask

  task.onOpen(() => {
    opened = true
    handlers.onOpen?.()
    resolveOpen?.()
  })

  task.onMessage((res) => {
    let data: PkStreamEvent
    try {
      data = typeof res.data === 'string' ? JSON.parse(res.data) : (res.data as any)
    } catch {
      return
    }
    switch (data.status) {
      case 'start':
        handlers.onStart?.(data)
        break
      case 'streaming':
        handlers.onChunk?.(data.chunk || '', data)
        break
      case 'end':
        handlers.onEnd?.(data)
        break
      case 'done':
        handlers.onDone?.(data.result, data)
        break
      case 'error':
        handlers.onError?.(data.message || '后端流式任务出错', data)
        break
    }
  })

  task.onError((err) => {
    const msg = (err as { errMsg?: string }).errMsg || 'WebSocket 连接错误'
    if (!opened) rejectOpen?.(new Error(msg))
    handlers.onError?.(msg, { status: 'error', message: msg })
  })

  task.onClose(() => {
    handlers.onClose?.()
    if (!opened) rejectOpen?.(new Error('WebSocket 提前关闭'))
  })

  return {
    task,
    whenOpen,
    close: () => {
      try {
        task.close({})
      } catch {
        /* noop */
      }
    },
  }
}

// ── 宠物对话（双向）──────────────────────────────────────────

export interface PetChatHistoryMessage {
  role: 'user' | 'assistant' | string
  content: string
  created_at?: string | null
}

export interface PetChatEvent extends PkStreamEvent {
  messages?: PetChatHistoryMessage[]
}

export interface PetChatHandlers {
  /** 连接建立后后端回放的历史消息 */
  onHistory?: (messages: PetChatHistoryMessage[]) => void
  /** 宠物开始回复（新建一条空气泡） */
  onStart?: () => void
  /** 流式 token */
  onChunk?: (chunk: string) => void
  /** 宠物回复结束 */
  onEnd?: () => void
  onError?: (message: string, event?: PetChatEvent) => void
  onOpen?: () => void
  onClose?: () => void
}

export interface PetChatConnection {
  task: UniApp.SocketTask
  whenOpen: Promise<void>
  /** 发送一条用户消息 */
  send: (text: string) => void
  close: () => void
}

export function connectPetChatStream(
  userId: string,
  petId: string | number,
  handlers: PetChatHandlers,
): PetChatConnection {
  const url = `${WS_BASE_URL}/ws/pet-chat/${encodeURIComponent(userId)}/${encodeURIComponent(String(petId))}`

  let resolveOpen: (() => void) | null = null
  let rejectOpen: ((err: Error) => void) | null = null
  let opened = false

  const whenOpen = new Promise<void>((resolve, reject) => {
    resolveOpen = resolve
    rejectOpen = reject
  })

  const task = uni.connectSocket({
    url,
    complete: () => {},
  }) as unknown as UniApp.SocketTask

  task.onOpen(() => {
    opened = true
    handlers.onOpen?.()
    resolveOpen?.()
  })

  task.onMessage((res) => {
    let data: PetChatEvent
    try {
      data = typeof res.data === 'string' ? JSON.parse(res.data) : (res.data as any)
    } catch {
      return
    }
    switch (data.status) {
      case 'history':
        handlers.onHistory?.(data.messages || [])
        break
      case 'start':
        handlers.onStart?.()
        break
      case 'streaming':
        handlers.onChunk?.(data.chunk || '')
        break
      case 'end':
        handlers.onEnd?.()
        break
      case 'error':
        handlers.onError?.(data.message || '宠物暂时无法回复', data)
        break
    }
  })

  task.onError((err) => {
    const msg = (err as { errMsg?: string }).errMsg || 'WebSocket 连接错误'
    if (!opened) rejectOpen?.(new Error(msg))
    handlers.onError?.(msg, { status: 'error', message: msg })
  })

  task.onClose(() => {
    handlers.onClose?.()
    if (!opened) rejectOpen?.(new Error('WebSocket 提前关闭'))
  })

  return {
    task,
    whenOpen,
    send: (text: string) => {
      task.send({ data: JSON.stringify({ content: text }) })
    },
    close: () => {
      try {
        task.close({})
      } catch {
        /* noop */
      }
    },
  }
}
