import { useCallback, useState } from 'react'
import type { ApiKeyStatus, ModelStatus } from '../types/timer'

interface SettingsProps {
  apiKeyStatus: ApiKeyStatus | null
  modelStatus: ModelStatus
  onSave: (key: string) => Promise<void>
  onClose: () => void
}

export function Settings({ apiKeyStatus, modelStatus, onSave, onClose }: SettingsProps) {
  const [value, setValue] = useState('')
  const [saving, setSaving] = useState(false)

  const handleSave = useCallback(async () => {
    const trimmed = value.trim()
    if (!trimmed) return
    setSaving(true)
    await onSave(trimmed)
    setSaving(false)
    setValue('')
  }, [value, onSave])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') handleSave()
    },
    [handleSave],
  )

  const statusLabel: Record<string, string> = {
    ready: 'Modelo cargado',
    downloading: 'Descargando…',
    pending: 'Iniciando…',
    error: 'Error al cargar modelo',
  }

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="settings-modal__header">
          <h2 className="settings-modal__title">Configuración</h2>
          <button className="settings-modal__close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="settings-modal__body">
          {/* ── Model section ── */}
          <div className="settings-modal__section">
            <h3 className="settings-modal__section-title">Modelo de voz (Whisper)</h3>

            <div className="settings-modal__model-status">
              <span className={`settings-modal__status-dot settings-modal__status-dot--${modelStatus.status}`} />
              <span>{statusLabel[modelStatus.status] || modelStatus.status}</span>
            </div>

            {modelStatus.status === 'downloading' && modelStatus.total > 0 && (
              <div className="settings-modal__progress-bar">
                <div
                  className="settings-modal__progress-fill"
                  style={{ width: `${Math.min(100, (modelStatus.current / modelStatus.total) * 100)}%` }}
                />
              </div>
            )}

            {modelStatus.status === 'downloading' && modelStatus.total > 0 && (
              <p className="settings-modal__progress-text">
                {Math.round((modelStatus.current / modelStatus.total) * 100)}%
                {' · '}
                {(modelStatus.total / 1024 / 1024).toFixed(0)} MB
              </p>
            )}
          </div>

          {/* ── API Key section ── */}
          <div className="settings-modal__section">
            <h3 className="settings-modal__section-title">API Key de Whisper</h3>

            <p className="settings-modal__desc">
              Agregá tu propia API key de OpenAI para usar Whisper en la nube y
              obtener transcripciones más precisas.
            </p>

            {apiKeyStatus?.has_key && (
              <div className="settings-modal__status">
                <span className="settings-modal__status-dot" />
                <span>Key configurada: <code>{apiKeyStatus.masked_key}</code></span>
              </div>
            )}

            <label className="settings-modal__label">
              OpenAI API Key
              <input
                className="settings-modal__input"
                type="password"
                placeholder={apiKeyStatus?.has_key ? 'Cambiar key…' : 'sk-proj-…'}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={handleKeyDown}
                autoComplete="off"
                spellCheck={false}
              />
            </label>

            <button
              className="settings-modal__save"
              disabled={saving || !value.trim()}
              onClick={handleSave}
            >
              {saving ? 'Guardando…' : 'Guardar'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
