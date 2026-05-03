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
