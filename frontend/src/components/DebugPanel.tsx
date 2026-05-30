import { useState } from 'react'
import type { ConnectionStatus } from '../types/timer'

interface DebugPanelProps {
  connectionStatus: ConnectionStatus
  timerCount: number
  sessionId: string
}

const STATUS_ICON: Record<ConnectionStatus, string> = {
  connected: '🟢',
  connecting: '🟡',
  disconnected: '🔴',
}

const STATUS_LABEL: Record<ConnectionStatus, string> = {
  connected: 'Conectado',
  connecting: 'Conectando...',
  disconnected: 'Desconectado',
}

export function DebugPanel({ connectionStatus, timerCount, sessionId }: DebugPanelProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className={`debug-panel ${open ? 'debug-panel--open' : ''}`}>
      <button className="debug-panel__toggle" onClick={() => setOpen((o) => !o)}>
        {open ? '▼' : '▲'} Debug
      </button>

      {open && (
        <div className="debug-panel__content">
          <div className="debug-panel__row">
            <span>WebSocket:</span>
            <span>{STATUS_ICON[connectionStatus]} {STATUS_LABEL[connectionStatus]}</span>
          </div>
          <div className="debug-panel__row">
            <span>Temporizadores:</span>
            <span>{timerCount}</span>
          </div>
          <div className="debug-panel__row">
            <span>Sesión:</span>
            <span className="debug-panel__mono">{sessionId.slice(0, 8)}…</span>
          </div>
        </div>
      )}
    </div>
  )
}
