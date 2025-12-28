import type { Event, StateSnapshot } from '@/net/contracts'

export type HelloPayload = {
  schema_version: 'v1'
  server_time_ms: number
  run_id: string | null
}

export type ErrorPayload = {
  schema_version: 'v1'
  message: string
  details: unknown | null
}

type WsEnvelope =
  | { type: 'HELLO'; payload: HelloPayload }
  | { type: 'SNAPSHOT'; payload: StateSnapshot }
  | { type: 'EVENT'; payload: Event }
  | { type: 'ERROR'; payload: ErrorPayload }

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected'

export type WsHandlers = {
  onHello?: (payload: HelloPayload) => void
  onSnapshot?: (payload: StateSnapshot) => void
  onEvent?: (payload: Event) => void
  onError?: (payload: ErrorPayload) => void
  onStatusChange?: (status: ConnectionStatus, error?: string) => void
}

const DEV_PORTS = new Set(['5173', '4173'])

export const getApiBaseUrl = (): string => {
  const envBase = import.meta.env.VITE_API_BASE as string | undefined
  if (envBase) {
    return envBase.replace(/\/$/, '')
  }
  const protocol = window.location.protocol === 'https:' ? 'https' : 'http'
  const hostname = window.location.hostname || '127.0.0.1'
  const port = DEV_PORTS.has(window.location.port) || !window.location.port ? '8000' : window.location.port
  return `${protocol}://${hostname}:${port}`
}

export const getWsUrl = (): string => {
  const envUrl = import.meta.env.VITE_WS_URL as string | undefined
  if (envUrl) {
    return envUrl
  }
  const base = getApiBaseUrl().replace(/^http/, 'ws')
  return `${base}/ws`
}

export class WsClient {
  private ws: WebSocket | null = null
  private retry = 0
  private reconnectTimer: number | null = null
  private shouldReconnect = true

  private readonly url: string;
  private readonly handlers: WsHandlers;

  constructor(url: string, handlers: WsHandlers) {
    this.url = url;
    this.handlers = handlers;
  }

  connect(): void {
    this.shouldReconnect = true
    this.handlers.onStatusChange?.('connecting')
    this.ws = new WebSocket(this.url)
    this.ws.onopen = () => {
      this.retry = 0
      this.handlers.onStatusChange?.('connected')
    }
    this.ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as WsEnvelope
        switch (parsed.type) {
          case 'HELLO':
            this.handlers.onHello?.(parsed.payload)
            break
          case 'SNAPSHOT':
            this.handlers.onSnapshot?.(parsed.payload)
            break
          case 'EVENT':
            this.handlers.onEvent?.(parsed.payload)
            break
          case 'ERROR':
            this.handlers.onError?.(parsed.payload)
            break
          default:
            break
        }
      } catch {
        this.handlers.onStatusChange?.('disconnected', 'Malformed message')
      }
    }
    this.ws.onclose = () => {
      this.handlers.onStatusChange?.('disconnected')
      if (this.shouldReconnect) {
        this.scheduleReconnect()
      }
    }
    this.ws.onerror = () => {
      this.handlers.onStatusChange?.('disconnected', 'WebSocket error')
    }
  }

  close(): void {
    this.shouldReconnect = false
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer !== null) {
      return
    }
    const delay = Math.min(500 * 2 ** this.retry, 5000)
    this.retry += 1
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null
      this.connect()
    }, delay)
  }
}
