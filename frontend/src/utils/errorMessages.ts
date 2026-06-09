export type ErrorCode =
  | 'empty_audio'
  | 'audio_too_large'
  | 'transcription_failed'
  | 'empty_transcription'
  | 'parse_error'
  | 'domain_error'
  | 'not_found'
  | 'network_error'
  | 'mic_permission_denied'
  | 'mic_not_available'
  | 'mic_https_required'
  | 'recording_empty'
  | 'api_key_error'
  | 'unknown'

export interface FriendlyError {
  code: ErrorCode
  title: string
  message: string
  kind: 'warning' | 'error' | 'info'
}

const ERROR_MAP: Record<ErrorCode, Omit<FriendlyError, 'code'>> = {
  empty_audio: {
    title: 'Ups, no recibí audio',
    message: 'Parece que el micrófono no está funcionando. ¿Puedes revisar si está conectado y encendido?',
    kind: 'warning',
  },
  audio_too_large: {
    title: 'El audio es muy largo',
    message: 'Intenta con comandos más cortos, así te entiendo mejor.',
    kind: 'warning',
  },
  transcription_failed: {
    title: 'No pude entender lo que dijiste',
    message: '¿Puedes intentar de nuevo? A veces el ruido de fondo me confunde.',
    kind: 'warning',
  },
  empty_transcription: {
    title: 'No te escuché bien',
    message: 'Si puedes, habla más alto y más despacio, así te entiendo mejor.',
    kind: 'warning',
  },
  parse_error: {
    title: 'Te escuché pero no entendí el comando',
    message: 'Prueba decir algo como "poner 10 minutos para la pasta" o "pausa el temporizador".',
    kind: 'info',
  },
  domain_error: {
    title: 'Algo salió mal',
    message: 'Esa acción no se puede hacer ahora mismo.',
    kind: 'warning',
  },
  not_found: {
    title: 'No encontré ese temporizador',
    message: 'Parece que ya no existe. Puedes crear uno nuevo.',
    kind: 'info',
  },
  network_error: {
    title: 'Error de conexión',
    message: 'No puedo comunicarme con el servidor. ¿Sigue encendido?',
    kind: 'error',
  },
  mic_permission_denied: {
    title: 'Necesito el micrófono',
    message: '¿Puedes permitir el acceso al micrófono desde la configuración del navegador?',
    kind: 'error',
  },
  mic_not_available: {
    title: 'No encontré un micrófono',
    message: '¿Tienes algún micrófono conectado a este dispositivo?',
    kind: 'error',
  },
  mic_https_required: {
    title: 'Se requiere una conexión segura',
    message: 'El micrófono solo funciona con HTTPS. ¿Estás usando una conexión segura?',
    kind: 'error',
  },
  recording_empty: {
    title: 'No te escuché',
    message: 'Parece que no dijiste nada. ¿Puedes intentar de nuevo hablando un poco más alto?',
    kind: 'warning',
  },
  api_key_error: {
    title: 'Error con la API key',
    message: 'La clave de OpenAI no es válida o no tiene créditos.',
    kind: 'error',
  },
  unknown: {
    title: 'Algo salió mal',
    message: 'Ocurrió un error inesperado. Inténtalo de nuevo.',
    kind: 'error',
  },
}

const KNOWN_CODES: Record<string, ErrorCode> = {
  empty_audio: 'empty_audio',
  audio_too_large: 'audio_too_large',
  transcription_failed: 'transcription_failed',
  empty_transcription: 'empty_transcription',
  parse_error: 'parse_error',
  domain_error: 'domain_error',
  not_found: 'not_found',
}

export function getFriendlyError(code: ErrorCode, detail?: string): FriendlyError {
  const entry = ERROR_MAP[code]
  if (detail && (code === 'domain_error' || code === 'unknown')) {
    return { code, ...entry, message: detail }
  }
  return { code, ...entry }
}

export function getErrorCodeFromBody(body: Record<string, unknown>): ErrorCode {
  if (body && typeof body.error === 'string') {
    return KNOWN_CODES[body.error] ?? 'unknown'
  }
  return 'unknown'
}
