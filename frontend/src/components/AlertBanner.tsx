import type { TimerAlert } from '../types/timer'

interface AlertBannerProps {
  alerts: TimerAlert[]
  onDismiss: (timerId: string) => void
}

export function AlertBanner({ alerts, onDismiss }: AlertBannerProps) {
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
