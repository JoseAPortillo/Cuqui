import { useCuquiApi } from './hooks/useCuquiApi'
import { TimerDashboard } from './components/TimerDashboard'
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
  const { timers, connectionStatus, alerts, sendAudio, dismissAlert, error, pauseTimer, resumeTimer, cancelTimer, deleteTimer, loadingTimers } = useCuquiApi()
  const sessionId = getSessionId()

  return (
    <div className="app">
      <AlertBanner alerts={alerts} onDismiss={dismissAlert} />

      <header className="app-header">
        <h1 className="app-header__title">Cuqui</h1>
        <p className="app-header__subtitle">Asistente de cocina inteligente</p>
      </header>

      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      <main className="app-main">
        <TimerDashboard
          timers={timers}
          onPause={pauseTimer}
          onResume={resumeTimer}
          onCancel={cancelTimer}
          onDelete={deleteTimer}
          loadingTimers={loadingTimers}
        />
      </main>

      <div className="voice-fixed">
        <VoiceButton onAudio={sendAudio} disabled={connectionStatus !== 'connected'} />
      </div>

      <DebugPanel
        connectionStatus={connectionStatus}
        timerCount={Object.keys(timers).length}
        sessionId={sessionId}
      />
    </div>
  )
}
