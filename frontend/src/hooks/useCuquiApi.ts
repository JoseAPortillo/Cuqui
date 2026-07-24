import { useCallback, useEffect, useRef, useState } from 'react'
import type { ApiKeyStatus, ConnectionStatus, Timer, TimerAlert } from '../types/timer'
import { getErrorCodeFromBody, getFriendlyError } from '../utils/errorMessages'
import type { FriendlyError } from '../utils/errorMessages'

function generateId(): string {
  return crypto.randomUUID?.() ?? Math.random().toString(36).slice(2)
}

const STORAGE_KEY = 'cuqui_session_id'

function getSessionId(): string {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored) return stored
  const id = generateId()
  localStorage.setItem(STORAGE_KEY, id)
  return id
}

const API_BASE = 'https://cuqui-app.duckdns.org'

interface CuquiApiState {
  timers: Record<string, Timer>
  connectionStatus: ConnectionStatus
  alerts: TimerAlert[]
  sendCommand: (text: string) => Promise<void>
  sendAudio: (audioBlob: Blob) => Promise<void>
  dismissAlert: (timerId: string) => void
  error: FriendlyError | null
  pauseTimer: (timerId: string) => Promise<void>
  resumeTimer: (timerId: string) => Promise<void>
  cancelTimer: (timerId: string) => Promise<void>
  deleteTimer: (timerId: string) => Promise<void>
  loadingTimers: Record<string, boolean>
  apiKeyStatus: ApiKeyStatus | null
  saveApiKey: (key: string) => Promise<void>
  checkApiKey: () => Promise<void>
}

export function useCuquiApi(): CuquiApiState {
  const sessionId = useRef(getSessionId())
  const wsRef = useRef<WebSocket | null>(null)
  const [timers, setTimers] = useState<Record<string, Timer>>({})
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const [alerts, setAlerts] = useState<TimerAlert[]>([])
  const [error, setApiError] = useState<FriendlyError | null>(null)
  const [loadingTimers, setLoadingTimers] = useState<Record<string, boolean>>({})
  const prevTimersRef = useRef<Record<string, Timer>>({})
  const hasLoadedRef = useRef(false)

  const connectWs = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setConnectionStatus('connecting')
    const url = `wss://cuqui-app.duckdns.org/ws/session/${sessionId.current}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setConnectionStatus('connected')
      setApiError(null)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.timers) {
          console.log('[WS] timers update:', data.timers)
          setTimers(data.timers)
        }
      } catch {
        console.warn('WS: invalid message', event.data)
      }
    }

    ws.onclose = () => {
      setConnectionStatus('disconnected')
      wsRef.current = null
      setTimeout(connectWs, 3000)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [])

  useEffect(() => {
    async function fetchTimers() {
      try {
        const res = await fetch(`${API_BASE}/timers?session_id=${sessionId.current}`)
        if (!res.ok) return
        const data: Timer[] = await res.json()
        const map: Record<string, Timer> = {}
        for (const t of data) {
          map[t.id] = t
        }
        setTimers(map)
        prevTimersRef.current = map
      } catch {
        console.warn('GET /timers failed')
      }
    }

    fetchTimers()
    connectWs()

    return () => {
      wsRef.current?.close()
    }
  }, [connectWs])

  useEffect(() => {
    const prev = prevTimersRef.current
    prevTimersRef.current = timers

    if (!hasLoadedRef.current) {
      if (Object.keys(timers).length > 0) {
        hasLoadedRef.current = true
      }
      return
    }

    const newAlerts: TimerAlert[] = []

    for (const [id, timer] of Object.entries(timers)) {
      const prevTimer = prev[id]
      if (timer.status === 'completed' && (!prevTimer || prevTimer.status !== 'completed')) {
        newAlerts.push({ timerId: id, timerName: timer.name })
      }
    }

    if (newAlerts.length > 0) {
      setAlerts((current) => [...current, ...newAlerts])
    }
  }, [timers])

  const sendCommand = useCallback(async (text: string) => {
    setApiError(null)
    try {
      const res = await fetch(`${API_BASE}/commands/text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, session_id: sessionId.current }),
      })

      if (!res.ok) {
        const body = await res.json()
        const code = getErrorCodeFromBody(body)
        setApiError(getFriendlyError(code, body.message))
        return
      }

      const timer: Timer = await res.json()
      console.log('[sendCommand] response:', timer)
      console.log('[sendCommand] status:', timer.status)
      setTimers((prev) => {
        console.log('[sendCommand] prev state:', prev, '-> merging:', timer.id, timer.status)
        return { ...prev, [timer.id]: timer }
      })
    } catch {
      setApiError(getFriendlyError('network_error'))
    }
  }, [])

  const sendAudio = useCallback(async (audioBlob: Blob) => {
    setApiError(null)
    try {
      const formData = new FormData()
      formData.append('audio', audioBlob, 'recording.wav')
      formData.append('session_id', sessionId.current)

      const res = await fetch(`${API_BASE}/commands/audio`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const body = await res.json()
        const code = getErrorCodeFromBody(body)
        setApiError(getFriendlyError(code, body.message))
        return
      }

      const timer: Timer = await res.json()
      setTimers((prev) => ({ ...prev, [timer.id]: timer }))
    } catch {
      setApiError(getFriendlyError('network_error'))
    }
  }, [])

  const dismissAlert = useCallback((timerId: string) => {
    setAlerts((current) => current.filter((a) => a.timerId !== timerId))
  }, [])

  const timerAction = useCallback(
    async (timerId: string, action: 'pause' | 'resume' | 'cancel') => {
      setApiError(null)
      setLoadingTimers((prev) => ({ ...prev, [timerId]: true }))
      try {
          const res = await fetch(`${API_BASE}/timers/${timerId}/${action}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId.current }),
        })

        if (!res.ok) {
          const body = await res.json()
          const code = getErrorCodeFromBody(body)
          setApiError(getFriendlyError(code, body.message))
          return
        }

        const timer: Timer = await res.json()
        setTimers((prev) => ({ ...prev, [timer.id]: timer }))
      } catch {
        setApiError(getFriendlyError('network_error'))
      } finally {
        setLoadingTimers((prev) => {
          const next = { ...prev }
          delete next[timerId]
          return next
        })
      }
    },
    [],
  )

  const pauseTimer = useCallback((timerId: string) => timerAction(timerId, 'pause'), [timerAction])
  const resumeTimer = useCallback((timerId: string) => timerAction(timerId, 'resume'), [timerAction])
  const cancelTimer = useCallback((timerId: string) => timerAction(timerId, 'cancel'), [timerAction])

  const deleteTimer = useCallback(async (timerId: string) => {
    setApiError(null)
    const sid = sessionId.current
    try {
      const res = await fetch(`${API_BASE}/timers/${timerId}?session_id=${encodeURIComponent(sid)}`, {
        method: 'DELETE',
      })

      if (!res.ok) {
        const body = await res.json()
        const code = getErrorCodeFromBody(body)
        setApiError(getFriendlyError(code, body.message))
        return
      }

      setTimers((prev) => {
        const next = { ...prev }
        delete next[timerId]
        return next
      })
    } catch {
      setApiError(getFriendlyError('network_error'))
    }
  }, [])

  const [apiKeyStatus, setApiKeyStatus] = useState<ApiKeyStatus | null>(null)

  const checkApiKey = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/settings/api-key?session_id=${encodeURIComponent(sessionId.current)}`)
      if (res.ok) {
        const data: ApiKeyStatus = await res.json()
        setApiKeyStatus(data)
      }
    } catch {
      console.warn('GET /settings/api-key failed')
    }
  }, [])

  const saveApiKey = useCallback(async (key: string) => {
    setApiError(null)
    try {
      const res = await fetch(`${API_BASE}/settings/api-key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId.current, api_key: key }),
      })
      if (!res.ok) {
        setApiError(getFriendlyError('api_key_error'))
        return
      }
      await checkApiKey()
    } catch {
      setApiError(getFriendlyError('network_error'))
    }
  }, [checkApiKey])

  useEffect(() => {
    checkApiKey()
  }, [checkApiKey])

  return {
    timers,
    connectionStatus,
    alerts,
    sendCommand,
    sendAudio,
    dismissAlert,
    error,
    pauseTimer,
    resumeTimer,
    cancelTimer,
    deleteTimer,
    loadingTimers,
    apiKeyStatus,
    saveApiKey,
    checkApiKey,
  }
}
