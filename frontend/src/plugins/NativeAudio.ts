import { registerPlugin } from '@capacitor/core'

export interface NativeAudioPlugin {
  startRecording(): Promise<{ started: boolean }>
  stopRecording(): Promise<{ audioData: string; sampleRate: number; channels: number; bitDepth: number }>
  isRecording(): Promise<{ recording: boolean }>
}

const NativeAudio = registerPlugin<NativeAudioPlugin>('NativeAudio')

export default NativeAudio
