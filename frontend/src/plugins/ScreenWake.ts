import { registerPlugin } from '@capacitor/core'

export interface ScreenWakePlugin {
  wakeScreen(): Promise<{ success: boolean }>
  releaseWakeLock(): Promise<{ released: boolean }>
}

const ScreenWake = registerPlugin<ScreenWakePlugin>('ScreenWake')

export default ScreenWake
