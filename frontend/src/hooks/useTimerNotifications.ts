import { useCallback, useEffect, useRef } from 'react'
import type { Timer } from '../types/timer'
import { CHIME_DATA_URI } from '../utils/chime'

const STORAGE_KEY = 'cuqui_session_id'

function getSessionId(): string {
  return localStorage.getItem(STORAGE_KEY) || ''
}

function urlBase64ToUint8Array(base64String: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  const buf = new ArrayBuffer(rawData.length)
  const view = new Uint8Array(buf)
  for (let i = 0; i < rawData.length; ++i) {
    view[i] = rawData.charCodeAt(i)
  }
  return view as Uint8Array<ArrayBuffer>
}

interface UseTimerNotificationsOptions {
  timers: Record<string, Timer>
}

export function useTimerNotifications({ timers }: UseTimerNotificationsOptions) {
  const swReady = useRef(false)
  const timersRef = useRef(timers)
  const pingInterval = useRef<ReturnType<typeof setInterval> | null>(null)
  const subscribed = useRef(false)

  timersRef.current = timers

  const sendToSW = useCallback((type: string, payload?: unknown) => {
    const controller = navigator.serviceWorker?.controller
    if (controller) {
      controller.postMessage({ type, payload })
    }
  }, [])

  const syncTimers = useCallback(() => {
    const running = Object.values(timersRef.current).filter((t) => t.status === 'running')
    sendToSW('TIMERS_SYNC', { timers: running })
  }, [sendToSW])

  const subscribeToPush = useCallback(async () => {
    if (subscribed.current) return
    try {
      const reg = await navigator.serviceWorker.ready
      const existing = await reg.pushManager.getSubscription()
      if (existing) {
        subscribed.current = true
        return
      }

      const res = await fetch('/push/vapid-public-key')
      if (!res.ok) return
      const { public_key } = await res.json()
      if (!public_key) return

      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(public_key),
      })

      const subJSON = sub.toJSON()
      await fetch('/push/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: getSessionId(),
          endpoint: subJSON.endpoint,
          p256dh: subJSON.keys?.p256dh || '',
          auth: subJSON.keys?.auth || '',
        }),
      })

      subscribed.current = true
    } catch {
      /* push subscription failed — app still works via SW timer sync */
    }
  }, [])

  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (!('Notification' in window)) return false
    if (Notification.permission === 'granted') {
      subscribeToPush()
      return true
    }
    if (Notification.permission === 'denied') return false
    const result = await Notification.requestPermission()
    if (result === 'granted') {
      subscribeToPush()
    }
    return result === 'granted'
  }, [subscribeToPush])

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      const { type } = event.data || {}
      if (type === 'TIMER_COMPLETED_FOCUS') {
        try {
          const audio = new Audio(CHIME_DATA_URI)
          audio.volume = 0.5
          audio.play().catch(() => {})
        } catch { /* ignore */ }
      }
    }

    navigator.serviceWorker?.addEventListener('message', handler)
    return () => navigator.serviceWorker?.removeEventListener('message', handler)
  }, [])

  useEffect(() => {
    if (!('serviceWorker' in navigator)) return

    function onReady() {
      swReady.current = true
      syncTimers()
      subscribeToPush()
    }

    if (navigator.serviceWorker.controller) {
      onReady()
    }

    navigator.serviceWorker.addEventListener('controllerchange', onReady)
    return () => navigator.serviceWorker.removeEventListener('controllerchange', onReady)
  }, [syncTimers, subscribeToPush])

  useEffect(() => {
    if (!swReady.current) return
    syncTimers()
  }, [timers, syncTimers])

  useEffect(() => {
    const hasRunning = Object.values(timers).some((t) => t.status === 'running')

    if (hasRunning && !pingInterval.current) {
      pingInterval.current = setInterval(() => {
        sendToSW('PING')
      }, 20000)
    }

    if (!hasRunning && pingInterval.current) {
      clearInterval(pingInterval.current)
      pingInterval.current = null
    }

    return () => {
      if (pingInterval.current) {
        clearInterval(pingInterval.current)
        pingInterval.current = null
      }
    }
  }, [timers, sendToSW])

  return { requestPermission }
}
