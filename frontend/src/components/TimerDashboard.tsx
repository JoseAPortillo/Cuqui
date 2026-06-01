import type { Timer } from '../types/timer'
import { TimerCard } from './TimerCard'

interface TimerDashboardProps {
  timers: Record<string, Timer>
  onPause?: (timerId: string) => void
  onResume?: (timerId: string) => void
  onCancel?: (timerId: string) => void
  loadingTimers?: Record<string, boolean>
}

export function TimerDashboard({ timers, onPause, onResume, onCancel, loadingTimers }: TimerDashboardProps) {
  const entries = Object.values(timers)

  if (entries.length === 0) {
    return (
      <div className="dashboard-empty">
        <p>No hay temporizadores activos</p>
        <p className="dashboard-empty__hint">
          Escribí un comando como <em>"poné 10 minutos para la pasta"</em>
        </p>
      </div>
    )
  }

  return (
    <div className="dashboard">
      {entries.map((timer) => (
        <TimerCard
          key={timer.id}
          timer={timer}
          onPause={onPause}
          onResume={onResume}
          onCancel={onCancel}
          disabled={loadingTimers?.[timer.id] ?? false}
        />
      ))}
    </div>
  )
}
