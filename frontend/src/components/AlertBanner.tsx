import { useEffect, useRef } from 'react'
import type { TimerAlert } from '../types/timer'
import { CHIME_DATA_URI } from '../utils/chime'

interface AlertBannerProps {
  alerts: TimerAlert[]
  onDismiss: (timerId: string) => void
}

export function AlertBanner({ alerts, onDismiss }: AlertBannerProps) {
  /** Tracks whether the user has interacted with the page (iOS Safari gate). */
  const hasInteracted = useRef(false)
  /** Set of timer IDs for which the chime has already been played. */
  const playedChimeTimers = useRef(new Set<string>())

  // Track first user interaction (click or touch) to satisfy iOS autoplay policy.
  useEffect(() => {
    function onInteraction() {
      hasInteracted.current = true
    }
    document.addEventListener('click', onInteraction, { once: true })
    document.addEventListener('touchstart', onInteraction, { once: true })
    return () => {
      document.removeEventListener('click', onInteraction)
      document.removeEventListener('touchstart', onInteraction)
    }
  }, [])

  // Play chime for each NEW timer completion (detected via unseen timerId).
  useEffect(() => {
    for (const alert of alerts) {
      if (playedChimeTimers.current.has(alert.timerId)) continue

      playedChimeTimers.current.add(alert.timerId)

      if (!hasInteracted.current) continue

      try {
        const audio = new Audio(CHIME_DATA_URI)
        audio.volume = 0.5
        audio.play().catch(() => {
          // Silently ignore — e.g. iOS policy, missing AudioContext, etc.
        })
      } catch {
        // Audio API not available — alert still shows visually.
      }
    }
  }, [alerts])

  if (alerts.length === 0) return null

  return (
    <div className="alert-banner">
      {alerts.map((alert) => (
        <div key={alert.timerId} className="alert-banner__item">
          <span className="alert-banner__text">
            ⏰ ¡{alert.timerName} — tiempo cumplido!
          </span>
          <button
            className="alert-banner__dismiss"
            onClick={() => onDismiss(alert.timerId)}
          >
            OK
          </button>
        </div>
      ))}
    </div>
  )
}
