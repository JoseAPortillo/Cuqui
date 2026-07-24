import { useCallback, useEffect, useRef, useState } from 'react'
import { getFriendlyError } from '../utils/errorMessages'
import type { FriendlyError } from '../utils/errorMessages'
import { isNativePlatform } from '../utils/platform'
import NativeAudio from '../plugins/NativeAudio'
import { pcmBase64ToWav } from '../utils/audioConvert'

interface VoiceButtonProps {
  onAudio: (blob: Blob) => Promise<void>
  disabled?: boolean
}

const MIN_AUDIO_SIZE = 1024

export function VoiceButton({ onAudio, disabled }: VoiceButtonProps) {
  const [recording, setRecording] = useState(false)
  const [error, setVoiceError] = useState<FriendlyError | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const [isNative, setIsNative] = useState(false)
  const [supported, setSupported] = useState(false)

  useEffect(() => {
    const native = isNativePlatform()
    console.log('[VoiceButton] isNativePlatform():', native, 'MediaRecorder:', typeof MediaRecorder)
    setIsNative(native)
    setSupported(native || typeof MediaRecorder !== 'undefined')
  }, [])

  const handleStart = useCallback(async () => {
    setVoiceError(null)
    console.log('[VoiceButton] handleStart - isNative:', isNative)

    if (isNative) {
      try {
        console.log('[VoiceButton] calling NativeAudio.startRecording()')
        await NativeAudio.startRecording()
        console.log('[VoiceButton] recording started')
        setRecording(true)
      } catch (err) {
        console.error('[VoiceButton] native error:', err)
        const msg = err instanceof Error ? err.message : String(err)
        if (msg.includes('permission') || msg.includes('Permission')) {
          setVoiceError(getFriendlyError('mic_permission_denied'))
        } else {
          setVoiceError(getFriendlyError('mic_not_available'))
        }
      }
      return
    }

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        setVoiceError(getFriendlyError('mic_not_available'))
        return
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      if (!stream.getAudioTracks().length) {
        stream.getTracks().forEach((t) => t.stop())
        setVoiceError(getFriendlyError('mic_not_available'))
        return
      }

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
          if (blob.size < MIN_AUDIO_SIZE) {
            setVoiceError(getFriendlyError('recording_empty'))
            return
          }
          await onAudio(blob)
        } else {
          setVoiceError(getFriendlyError('recording_empty'))
        }
      }

      mediaRecorderRef.current = recorder
      recorder.start()
      setRecording(true)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      if (msg.includes('Permission') || msg.includes('permission')) {
        setVoiceError(getFriendlyError('mic_permission_denied'))
      } else if (msg.includes('NotFoundError') || msg.includes('not found')) {
        setVoiceError(getFriendlyError('mic_not_available'))
      } else if (msg.includes('secure')) {
        setVoiceError(getFriendlyError('mic_https_required'))
      } else {
        setVoiceError(getFriendlyError('mic_not_available'))
      }
    }
  }, [onAudio, isNative])

  const handleStop = useCallback(async () => {
    if (isNative) {
      try {
        const result = await NativeAudio.stopRecording()
        const wav = pcmBase64ToWav(result.audioData, result.sampleRate, result.channels, result.bitDepth)
        if (wav.size < MIN_AUDIO_SIZE) {
          setVoiceError(getFriendlyError('recording_empty'))
          setRecording(false)
          return
        }
        setRecording(false)
        await onAudio(wav)
      } catch (err) {
        setVoiceError(getFriendlyError('recording_empty'))
        setRecording(false)
      }
      return
    }

    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
    setRecording(false)
  }, [onAudio, isNative])

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
      {error && (
        <div className={`voice-btn__error voice-btn__error--${error.kind}`}>
          {error.message}
        </div>
      )}
    </div>
  )
}
