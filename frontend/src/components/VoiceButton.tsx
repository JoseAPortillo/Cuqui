import { useCallback, useRef, useState } from 'react'

interface VoiceButtonProps {
  onAudio: (blob: Blob) => Promise<void>
  disabled?: boolean
}

function isMediaRecorderSupported(): boolean {
  return typeof MediaRecorder !== 'undefined'
}

export function VoiceButton({ onAudio, disabled }: VoiceButtonProps) {
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const [supported] = useState(isMediaRecorderSupported)

  const handleStart = useCallback(async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm'
      const recorder = new MediaRecorder(stream, { mimeType: mime })
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType })
        if (blob.size > 0) {
          await onAudio(blob)
        }
      }

      mediaRecorderRef.current = recorder
      recorder.start()
      setRecording(true)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      if (msg.includes('Permission')) {
        setError('Permiso de micrófono denegado')
      } else if (msg.includes('secure')) {
        setError('Se requiere HTTPS para usar el micrófono')
      } else {
        setError('Error al acceder al micrófono')
      }
    }
  }, [onAudio])

  const handleStop = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
    setRecording(false)
  }, [])

  if (!supported) return null

  return (
    <div className="voice-section">
      <button
        className={`voice-btn ${recording ? 'voice-btn--recording' : ''}`}
        title={recording ? 'Grabando...' : 'Presiona y habla'}
        disabled={disabled}
        onMouseDown={handleStart}
        onMouseUp={handleStop}
        onMouseLeave={handleStop}
        onTouchStart={handleStart}
        onTouchEnd={handleStop}
        onTouchCancel={handleStop}
      >
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="23" />
          <line x1="8" y1="23" x2="16" y2="23" />
        </svg>
      </button>
      <span className="voice-btn__label">
        {recording ? 'Grabando... suelta para enviar' : 'Presiona y habla'}
      </span>
      {error && <span className="voice-btn__error">{error}</span>}
    </div>
  )
}
