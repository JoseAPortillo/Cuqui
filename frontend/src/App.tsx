import { useEffect, useRef, useState } from 'react'
import { useCuquiApi } from './hooks/useCuquiApi'
import { useTimerNotifications } from './hooks/useTimerNotifications'
import { TimerDashboard } from './components/TimerDashboard'
import { VoiceButton } from './components/VoiceButton'
import { AlertBanner } from './components/AlertBanner'
import { DebugPanel } from './components/DebugPanel'
import { CommandsHelp } from './components/CommandsHelp'
import { ApiKeySettings } from './components/ApiKeySettings'
import './App.css'

function getSessionId(): string {
  const stored = localStorage.getItem('cuqui_session_id')
  if (stored) return stored
  const id = crypto.randomUUID?.() ?? Math.random().toString(36).slice(2)
  localStorage.setItem('cuqui_session_id', id)
  return id
}

export default function App() {
  const { timers, connectionStatus, alerts, sendAudio, dismissAlert, error, pauseTimer, resumeTimer, cancelTimer, deleteTimer, loadingTimers, apiKeyStatus, saveApiKey } = useCuquiApi()
  const sessionId = getSessionId()
  const [showApiKey, setShowApiKey] = useState(false)

  const { requestPermission } = useTimerNotifications({ timers })
  const permissionRequested = useRef(false)

  useEffect(() => {
    const hasTimers = Object.keys(timers).length > 0
    if (hasTimers && !permissionRequested.current) {
      permissionRequested.current = true
      requestPermission()
    }
  }, [timers, requestPermission])

  return (
    <div className="app">
      <AlertBanner alerts={alerts} onDismiss={dismissAlert} />

      <CommandsHelp />

      {showApiKey && (
        <ApiKeySettings
          apiKeyStatus={apiKeyStatus}
          onSave={saveApiKey}
          onClose={() => setShowApiKey(false)}
        />
      )}

      <header className="app-header">
        <h1 className="app-header__title">Cuqui</h1>
        <p className="app-header__subtitle">Asistente de cocina inteligente</p>
      </header>

      <button
        className="settings-btn"
        title="Configurar API key"
        onClick={() => setShowApiKey(true)}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="3" />
          <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
        </svg>
      </button>

      {error && (
        <div className={`error-banner error-banner--${error.kind}`}>
          <div className="error-banner__title">{error.title}</div>
          <div className="error-banner__message">{error.message}</div>
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
