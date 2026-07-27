import { registerPlugin } from '@capacitor/core'

export interface VibratePlugin {
  vibrateAlarm(): Promise<{ success: boolean }>
  vibrateShort(): Promise<{ success: boolean }>
  cancelVibration(): Promise<{ cancelled: boolean }>
}

const Vibrate = registerPlugin<VibratePlugin>('Vibrate')

export default Vibrate
