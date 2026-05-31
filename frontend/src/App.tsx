import { useCuquiApi } from './hooks/useCuquiApi'
import { TimerDashboard } from './components/TimerDashboard'
import { CommandInput } from './components/CommandInput'
import { VoiceButton } from './components/VoiceButton'
import { AlertBanner } from './components/AlertBanner'
import { DebugPanel } from './components/DebugPanel'
import './App.css'

function getSessionId(): string {
  const stored = localStorage.getItem('cuqui_session_id')
  if (stored) return stored
  const id = crypto.randomUUID?.() ?? Math.random().toString(36).slice(2)
  localStorage.setItem('cuqui_session_id', id)
  return id
}

export default function App() {
  const { timers, connectionStatus, alerts, sendCommand, sendAudio, dismissAlert, error } = useCuquiApi()
  const sessionId = getSessionId()

  return (
    <div className="app">
      <AlertBanner alerts={alerts} onDismiss={dismissAlert} />

      <header className="app-header">
        <h1 className="app-header__title">Cuqui</h1>
        <p className="app-header__subtitle">Asistente de cocina inteligente</p>
      </header>

      <main className="app-main">
        <div className="input-row">
          <CommandInput onSend={sendCommand} disabled={connectionStatus !== 'connected'} />
          <VoiceButton onAudio={sendAudio} disabled={connectionStatus !== 'connected'} />
        </div>

        {error && (
          <div className="error-banner">
            {error}
          </div>
        )}

        <TimerDashboard timers={timers} />
      </main>

      <DebugPanel
        connectionStatus={connectionStatus}
        timerCount={Object.keys(timers).length}
        sessionId={sessionId}
      />
    </div>
  )
}
