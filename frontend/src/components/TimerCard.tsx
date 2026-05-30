import type { Timer } from '../types/timer'

interface TimerCardProps {
  timer: Timer
}

const STATUS_LABELS: Record<string, string> = {
  running: 'En curso',
  paused: 'En pausa',
  completed: 'Completado',
  cancelled: 'Cancelado',
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function progressPercent(timer: Timer): number {
  if (timer.duration === 0) return 0
  return Math.max(0, Math.min(100, ((timer.duration - timer.remaining) / timer.duration) * 100))
}

export function TimerCard({ timer }: TimerCardProps) {
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
