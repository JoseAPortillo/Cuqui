import type { Timer } from '../types/timer'

interface TimerCardProps {
  timer: Timer
  onPause?: (timerId: string) => void
  onResume?: (timerId: string) => void
  onCancel?: (timerId: string) => void
  disabled?: boolean
}

const STATUS_LABELS: Record<string, string> = {
  running: 'En curso',
  paused: 'En pausa',
  completed: 'Completado',
  cancelled: 'Cancelado',
}

function formatTime(seconds: number): string {
  if (seconds >= 86400) {
    const d = Math.floor(seconds / 86400)
    const h = Math.floor((seconds % 86400) / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    return `${d}d ${h}h ${m}m`
  }
  if (seconds >= 3600) {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = seconds % 60
    return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function progressPercent(timer: Timer): number {
  if (timer.duration === 0) return 0
  return Math.max(0, Math.min(100, ((timer.duration - timer.remaining) / timer.duration) * 100))
}

export function TimerCard({ timer, onPause, onResume, onCancel, disabled }: TimerCardProps) {
  const pct = progressPercent(timer)
  const isComplete = timer.status === 'completed'
  const isCancelled = timer.status === 'cancelled'
  const faded = isComplete || isCancelled

  return (
    <div className={`timer-card timer-card--${timer.status}`}>
      <div className="timer-card__header">
        <span className="timer-card__name">{timer.name}</span>
        <span className={`timer-card__status timer-card__status--${timer.status}`}>
          {STATUS_LABELS[timer.status]}
        </span>
      </div>

      <div className="timer-card__time">
        {formatTime(timer.remaining)}
      </div>

      <div className="timer-card__progress">
        <div
          className={`timer-card__progress-fill timer-card__progress-fill--${timer.status}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {!faded && (onPause || onResume || onCancel) && (
        <div className="timer-card__actions">
          {timer.status === 'running' && onPause && (
            <button
              className="timer-card__btn timer-card__btn--pause"
              onClick={() => onPause(timer.id)}
              disabled={disabled}
            >
              Pausar
            </button>
          )}
          {timer.status === 'paused' && onResume && (
            <button
              className="timer-card__btn timer-card__btn--resume"
              onClick={() => onResume(timer.id)}
              disabled={disabled}
            >
              Reanudar
            </button>
          )}
          {onCancel && (
            <button
              className="timer-card__btn timer-card__btn--cancel"
              onClick={() => onCancel(timer.id)}
              disabled={disabled}
            >
              Cancelar
            </button>
          )}
        </div>
      )}

      <div className="timer-card__footer">
        {faded ? (
          <span className="timer-card__footer-text">
            {isComplete ? '¡Tiempo cumplido!' : 'Cancelado'}
          </span>
        ) : (
          <span className="timer-card__footer-text">
            Total: {formatTime(timer.duration)}
          </span>
        )}
      </div>
    </div>
  )
}
