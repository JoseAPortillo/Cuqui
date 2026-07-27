import { registerPlugin } from '@capacitor/core'

export interface AlarmPlugin {
  schedule(options: { timerId: string; timerName: string; seconds: number }): Promise<{ success: boolean; timerId: string }>
  cancel(options: { timerId: string }): Promise<{ success: boolean; timerId: string }>
}

const Alarm = registerPlugin<AlarmPlugin>('Alarm')

export default Alarm
