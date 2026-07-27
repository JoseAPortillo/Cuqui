import { useCallback, useEffect, useRef } from 'react'
import type { Timer } from '../types/timer'
import { CHIME_DATA_URI } from '../utils/chime'
import { useCapacitor } from './useCapacitor'
import Alarm from '../plugins/Alarm'

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

const MAX_PUSH_RETRIES = 3
const PUSH_RETRY_DELAY = 5000

async function registerPush(sessionId: string): Promise<void> {
  const reg = await navigator.serviceWorker.ready
  const existing = await reg.pushManager.getSubscription()

  const sub = existing
    ? existing
    : await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(
          await fetchVapidKey(),
        ),
      })

  const subJSON = sub.toJSON()
  await fetch('https://cuqui-app.duckdns.org/push/subscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      endpoint: subJSON.endpoint,
      p256dh: subJSON.keys?.p256dh || '',
      auth: subJSON.keys?.auth || '',
    }),
  })
}

async function registerPushWithRetry(sessionId: string): Promise<void> {
  for (let i = 0; i < MAX_PUSH_RETRIES; i++) {
    try {
      await registerPush(sessionId)
      return
    } catch {
      if (i < MAX_PUSH_RETRIES - 1) {
        await new Promise((r) => setTimeout(r, PUSH_RETRY_DELAY))
      }
    }
  }
}

async function fetchVapidKey(): Promise<string> {
  const res = await fetch('https://cuqui-app.duckdns.org/push/vapid-public-key')
  if (!res.ok) throw new Error('Failed to fetch VAPID key')
  const { public_key } = await res.json()
  if (!public_key) throw new Error('No VAPID public key')
  return public_key
}

interface UseTimerNotificationsOptions {
  timers: Record<string, Timer>
}

const ALARM_LOOP_MS = 900

export function useTimerNotifications({ timers }: UseTimerNotificationsOptions) {
  const swReady = useRef(false)
  const timersRef = useRef(timers)
  const pingInterval = useRef<ReturnType<typeof setInterval> | null>(null)
  const pushRegistered = useRef(false)
  const playingAlarms = useRef(new Set<string>())
    const alarmIntervals = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map())
  const { isNative } = useCapacitor()

  timersRef.current = timers

  const playAlarm = useCallback((timerId: string) => {
    if (playingAlarms.current.has(timerId)) return
    playingAlarms.current.add(timerId)

    function playChime() {
      try {
        const audio = new Audio(CHIME_DATA_URI)
        audio.volume = 0.7
        audio.play().catch(() => {})
      } catch { /* ignore */ }
    }

    playChime()

    // Chime every 900ms for in-app feedback
    const chimeInterval = setInterval(playChime, ALARM_LOOP_MS)
    alarmIntervals.current.set(timerId, chimeInterval)
  }, [])

  const stopAlarm = useCallback((timerId: string) => {
    const interval = alarmIntervals.current.get(timerId)
    if (interval) {
      clearInterval(interval)
      alarmIntervals.current.delete(timerId)
    }
    playingAlarms.current.delete(timerId)
  }, [])

  const stopAllAlarms = useCallback(() => {
    for (const [, interval] of alarmIntervals.current) {
      clearInterval(interval)
    }
    alarmIntervals.current.clear()
    playingAlarms.current.clear()
  }, [])

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

  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (!('Notification' in window)) return false
    if (Notification.permission === 'denied') return false

    const result = Notification.permission === 'granted'
      ? 'granted'
      : await Notification.requestPermission()

    if (result === 'granted' && !pushRegistered.current) {
      pushRegistered.current = true
      registerPushWithRetry(getSessionId())
    }

    return result === 'granted'
  }, [])

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      const { type, payload } = event.data || {}
      if (type === 'SHOW_ALARM' && payload?.timerId) {
        playAlarm(payload.timerId)
      } else if (type === 'STOP_ALARM' && payload?.timerId) {
        stopAlarm(payload.timerId)
      } else if (type === 'TIMER_COMPLETED_FOCUS') {
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
      if (!pushRegistered.current) {
        pushRegistered.current = true
        registerPushWithRetry(getSessionId())
      }
    }

    if (navigator.serviceWorker.controller) {
      onReady()
    }

    navigator.serviceWorker.addEventListener('controllerchange', onReady)
    return () => navigator.serviceWorker.removeEventListener('controllerchange', onReady)
  }, [syncTimers])

  const scheduledAlarmsRef = useRef<Map<string, number>>(new Map())

  const scheduleNativeAlarm = useCallback(async (timerId: string, timerName: string, seconds: number) => {
    if (!isNative) return
    try {
      console.log('[scheduleNativeAlarm] Calling Alarm.schedule with seconds:', seconds)
      await Alarm.schedule({ timerId, timerName, seconds })
    } catch { /* ignore */ }
  }, [isNative])

  const cancelNativeAlarm = useCallback(async (timerId: string) => {
    if (!isNative) return
    try {
      await Alarm.cancel({ timerId })
    } catch { /* ignore */ }
  }, [isNative])

  useEffect(() => {
    if (!swReady.current) return
    syncTimers()

    const timerIds = new Set(Object.keys(timers))
    for (const alarmId of playingAlarms.current) {
      if (!timerIds.has(alarmId)) {
        stopAlarm(alarmId)
      }
    }

    if (isNative) {
      const running = Object.values(timers).filter((t) => t.status === 'running')
      const runningIds = new Set(running.map((t) => t.id))
      const completedIds = new Set(Object.values(timers).filter((t) => t.status === 'completed').map((t) => t.id))

      async function updateAlarms() {
        // Cancel native alarms for timers that were explicitly stopped/removed (not completed or running)
        const toCancel: string[] = []
        for (const [timerId] of scheduledAlarmsRef.current) {
          if (!runningIds.has(timerId) && !completedIds.has(timerId)) {
            toCancel.push(timerId)
          }
        }
        for (const timerId of toCancel) {
          await cancelNativeAlarm(timerId)
          scheduledAlarmsRef.current.delete(timerId)
        }

        // Schedule native alarms for running timers (only once when timer starts)
        for (const timer of running) {
          if (!scheduledAlarmsRef.current.has(timer.id) && timer.remaining > 0) {
            console.log('[useTimerNotifications] Scheduling native alarm for timer', timer.id, 'remaining:', timer.remaining, 'duration:', timer.duration, 'status:', timer.status)
            await scheduleNativeAlarm(timer.id, timer.name, timer.remaining)
            scheduledAlarmsRef.current.set(timer.id, timer.remaining)
          }
        }
      }

      updateAlarms()
    }
  }, [timers, syncTimers, isNative, cancelNativeAlarm, scheduleNativeAlarm])

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

  const initialCheckDone = useRef(false)
  const timersOnHide = useRef<Record<string, Timer>>({})

  useEffect(() => {
    if (initialCheckDone.current) return
    if (Object.keys(timers).length === 0) return

    initialCheckDone.current = true

    const now = Date.now()
    const RECENT_MS = 5 * 60 * 1000

    for (const timer of Object.values(timers)) {
      if (
        timer.status === 'completed'
        && timer.completed_at
        && now - new Date(timer.completed_at).getTime() < RECENT_MS
        && !playingAlarms.current.has(timer.id)
      ) {
        playAlarm(timer.id)
      }
    }
  }, [timers])

  useEffect(() => {
    function onVisibilityChange() {
      if (document.visibilityState === 'hidden') {
        timersOnHide.current = { ...timersRef.current }
      } else if (document.visibilityState === 'visible') {
        const prev = timersOnHide.current
        for (const [id, timer] of Object.entries(timersRef.current)) {
          const prevTimer = prev[id]
          if (timer.status === 'completed' && (!prevTimer || prevTimer.status !== 'completed')) {
            if (!playingAlarms.current.has(id)) {
              playAlarm(id)
            }
          }
        }
      }
    }

    document.addEventListener('visibilitychange', onVisibilityChange)
    return () => document.removeEventListener('visibilitychange', onVisibilityChange)
  }, [])

  return { requestPermission, stopAllAlarms, stopAlarm, playAlarm }
}
