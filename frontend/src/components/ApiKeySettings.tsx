import { useCallback, useState } from 'react'
import type { ApiKeyStatus } from '../types/timer'

interface ApiKeySettingsProps {
  apiKeyStatus: ApiKeyStatus | null
  onSave: (key: string) => Promise<void>
  onClose: () => void
}

export function ApiKeySettings({ apiKeyStatus, onSave, onClose }: ApiKeySettingsProps) {
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

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="settings-modal__header">
          <h2 className="settings-modal__title">API Key de Whisper</h2>
          <button className="settings-modal__close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="settings-modal__body">
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
  )
}
