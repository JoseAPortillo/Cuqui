import { useCallback, useEffect, useRef, useState } from 'react'
import type { ConnectionStatus, Timer, TimerAlert } from '../types/timer'

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

interface CuquiApiState {
  timers: Record<string, Timer>
  connectionStatus: ConnectionStatus
  alerts: TimerAlert[]
  sendCommand: (text: string) => Promise<void>
  dismissAlert: (timerId: string) => void
  error: string | null
}

export function useCuquiApi(): CuquiApiState {
  const sessionId = useRef(getSessionId())
  const wsRef = useRef<WebSocket | null>(null)
  const [timers, setTimers] = useState<Record<string, Timer>>({})
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const [alerts, setAlerts] = useState<TimerAlert[]>([])
  const [error, setError] = useState<string | null>(null)
  const prevTimersRef = useRef<Record<string, Timer>>({})

  const connectWs = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setConnectionStatus('connecting')
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/ws/session/${sessionId.current}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setConnectionStatus('connected')
      setError(null)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.timers) {
          console.log('[WS] timers update:', data.timers)
          setTimers((prev) => {
            prevTimersRef.current = prev
            return data.timers
          })
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
        const res = await fetch(`/timers?session_id=${sessionId.current}`)
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
    setError(null)
    try {
      const res = await fetch('/commands/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, session_id: sessionId.current }),
      })

      if (!res.ok) {
        const body = await res.json()
        setError(body.message ?? body.error ?? 'Error desconocido')
        return
      }

      const timer: Timer = await res.json()
      console.log('[sendCommand] response:', timer)
      console.log('[sendCommand] status:', timer.status)
      setTimers((prev) => {
        console.log('[sendCommand] prev state:', prev, '-> merging:', timer.id, timer.status)
        return { ...prev, [timer.id]: timer }
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error de red')
    }
  }, [])

  const dismissAlert = useCallback((timerId: string) => {
    setAlerts((current) => current.filter((a) => a.timerId !== timerId))
  }, [])

  return { timers, connectionStatus, alerts, sendCommand, dismissAlert, error }
}
