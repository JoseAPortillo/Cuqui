export function pcmBase64ToWav(base64: string, sampleRate: number, channels: number, bitDepth: number): Blob {
  const pcmData = Uint8Array.from(atob(base64), c => c.charCodeAt(0))
  const bytesPerSample = bitDepth / 8
  const dataLength = pcmData.length
  const headerLength = 44
  const totalLength = headerLength + dataLength
  const buffer = new ArrayBuffer(totalLength)
  const view = new DataView(buffer)

  const writeString = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i))
    }
  }

  writeString(0, 'RIFF')
  view.setUint32(4, totalLength - 8, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, channels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * channels * bytesPerSample, true)
  view.setUint16(32, channels * bytesPerSample, true)
  view.setUint16(34, bitDepth, true)
  writeString(36, 'data')
  view.setUint32(40, dataLength, true)

  const pcmArray = new Uint8Array(buffer, headerLength)
  pcmArray.set(pcmData)

  return new Blob([buffer], { type: 'audio/wav' })
}
