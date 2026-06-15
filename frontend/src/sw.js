self.__WB_MANIFEST

const RUNNING_TIMERS = new Map()

async function ensureAudioCtx() {
  const ctx = new AudioContext()
  if (ctx.state === 'suspended') {
    await ctx.resume()
  }
  const timeout = new Promise((_, reject) =>
    setTimeout(() => reject(new Error('resume timeout')), 3000),
  )
  await Promise.race([
    new Promise((resolve) => {
      if (ctx.state === 'running') return resolve()
      ctx.onstatechange = () => {
        if (ctx.state === 'running') {
          ctx.onstatechange = null
          resolve()
        }
      }
    }),
    timeout,
  ])
  return ctx
}

async function playAlarmBeeps() {
  try {
    const audioCtx = await ensureAudioCtx()
    const now = audioCtx.currentTime
    const beeps = 8
    const beepLen = 0.25
    const pause = 0.25
    const cycle = beepLen + pause

    const osc = audioCtx.createOscillator()
    osc.type = 'sawtooth'

    const gain = audioCtx.createGain()
    gain.gain.setValueAtTime(0, now)

    for (let i = 0; i < beeps; i++) {
      const t = now + i * cycle
      osc.frequency.setValueAtTime(i % 2 === 0 ? 880 : 660, t)
      gain.gain.setValueAtTime(0.5, t)
      gain.gain.setValueAtTime(0, t + beepLen)
    }

    osc.connect(gain)
    gain.connect(audioCtx.destination)
    osc.start(now)
    osc.stop(now + beeps * cycle)

    return new Promise((r) => setTimeout(r, beeps * cycle * 1000 + 200))
  } catch {
    return Promise.resolve()
  }
}

self.addEventListener('install', () => {
  self.skipWaiting()
})

async function warmAudioPipeline() {
  try {
    const ctx = await ensureAudioCtx()
    ctx.close()
  } catch {
    /* warm-up failed — alarm will try fresh AudioContext per push */
  }
}

self.addEventListener('activate', (event) => {
  event.waitUntil(Promise.all([
    self.clients.claim(),
    warmAudioPipeline(),
  ]))
})

self.addEventListener('push', (event) => {
  let data = { title: '\u23F0 \u00a1Tiempo cumplido!', body: '', tag: 'cuqui-push', data: {} }
  if (event.data) {
    try {
      data = event.data.json()
    } catch { /* use defaults */ }
  }

  const options = {
    body: data.body || '',
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-192.png',
    vibrate: [200, 100, 200, 100, 300],
    tag: data.tag || 'cuqui-push',
    renotify: true,
    requireInteraction: true,
    silent: data.silent === true,
    data: data.data || {},
  }

  const broadcastAlarm = clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
    for (const client of list) {
      client.postMessage({
        type: 'SHOW_ALARM',
        payload: { timerId: data.data?.timerId, timerName: data.data?.timerName },
      })
    }
  })

  event.waitUntil(
    Promise.all([
      self.registration.showNotification(data.title, options).catch(() => {}),
      playAlarmBeeps(),
      broadcastAlarm,
    ]),
  )
})

self.addEventListener('message', (event) => {
  const { type, payload } = event.data || {}

  switch (type) {
    case 'TIMERS_SYNC':
      syncTimers(payload?.timers || [])
      break
    case 'TIMER_COMPLETED':
      clearTimer(payload?.id)
      break
    case 'TIMER_CANCELLED':
      clearTimer(payload?.id)
      break
    case 'PING':
      event.source?.postMessage({ type: 'PONG' })
      break
  }
})

function syncTimers(timers) {
  clearAllTimers()

  const now = Date.now()
  for (const t of timers) {
    if (t.status !== 'running') continue

    const remainingMs = (t.remaining || 0) * 1000
    if (remainingMs <= 0) continue

    const timeout = setTimeout(() => fireNotification(t), remainingMs)
    RUNNING_TIMERS.set(t.id, { name: t.name, timeout })
  }
}

function fireNotification(timer) {
  RUNNING_TIMERS.delete(timer.id)

  const broadcastAlarm = clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
    for (const client of list) {
      client.postMessage({
        type: 'SHOW_ALARM',
        payload: { timerId: timer.id, timerName: timer.name },
      })
    }
  })

  Promise.all([
    self.registration.showNotification('\u23F0 \u00a1Tiempo cumplido!', {
      body: `"${timer.name}" — el temporizador termin\u00f3.`,
      icon: '/icons/icon-192.png',
      badge: '/icons/icon-192.png',
      vibrate: [200, 100, 200, 100, 300],
      tag: `timer-${timer.id}`,
      renotify: true,
      requireInteraction: true,
      silent: false,
      data: { timerId: timer.id, timerName: timer.name },
    }).catch(() => {}),
    playAlarmBeeps(),
    broadcastAlarm,
  ])
}

function clearTimer(id) {
  const existing = RUNNING_TIMERS.get(id)
  if (existing) {
    clearTimeout(existing.timeout)
    RUNNING_TIMERS.delete(id)
  }
}

function clearAllTimers() {
  for (const [, entry] of RUNNING_TIMERS) {
    clearTimeout(entry.timeout)
  }
  RUNNING_TIMERS.clear()
}

self.addEventListener('notificationclick', (event) => {
  event.notification.close()

  const data = event.notification.data || {}

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      for (const client of list) {
        if (client.url && 'focus' in client) {
          client.postMessage({
            type: 'STOP_ALARM',
            payload: { timerId: data.timerId },
          })
          client.postMessage({
            type: 'TIMER_COMPLETED_FOCUS',
            payload: { timerId: data.timerId, timerName: data.timerName },
          })
          return client.focus()
        }
      }
      if (clients.openWindow) {
        return clients.openWindow('/')
      }
    }),
  )
})
