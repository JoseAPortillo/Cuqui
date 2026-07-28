export type TimerStatus = 'running' | 'paused' | 'completed' | 'cancelled'

export interface Timer {
  id: string
  name: string
  duration: number
  remaining: number
  status: TimerStatus
  created_at: string
  completed_at?: string
}

export interface TimerState {
  timers: Record<string, Timer>
}

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected'

export interface TimerAlert {
  timerId: string
  timerName: string
}

export interface ApiKeyStatus {
  has_key: boolean
  masked_key: string | null
}

export interface ModelStatus {
  status: 'pending' | 'downloading' | 'ready' | 'error'
  current: number
  total: number
  description: string
}
