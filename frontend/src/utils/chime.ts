/**
 * Synthesized notification chime as a base64-encoded WAV data URI.
 *
 * Generates a short two-tone chime (880Hz + 1320Hz) with fade-in/out
 * envelope. Pure computation — no AudioContext, no external files.
 *
 * Format: 44100 Hz, 16-bit mono PCM WAV, ~500ms duration.
 */

function generateChimeDataUri(): string {
  const sampleRate = 44100
  const durationSec = 0.5
  const numSamples = Math.floor(sampleRate * durationSec)
  const numChannels = 1
  const bitsPerSample = 16
  const bytesPerSample = bitsPerSample / 8
  const blockAlign = numChannels * bytesPerSample
  const byteRate = sampleRate * blockAlign
  const dataSize = numSamples * blockAlign
  const headerSize = 44
  const bufferSize = headerSize + dataSize

  const buffer = new ArrayBuffer(bufferSize)
  const view = new DataView(buffer)

  // ── WAV header ────────────────────────────────────────────
  writeString(view, 0, 'RIFF')
  view.setUint32(4, bufferSize - 8, true)        // file size - 8
  writeString(view, 8, 'WAVE')

  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true)                   // chunk size (PCM)
  view.setUint16(20, 1, true)                    // PCM format
  view.setUint16(22, numChannels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, byteRate, true)
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, bitsPerSample, true)

  writeString(view, 36, 'data')
  view.setUint32(40, dataSize, true)

  // ── Synthesize samples ────────────────────────────────────
  const freq1 = 880    // A5 — base tone
  const freq2 = 1320   // E6 — perfect fifth above
  const fadeLen = Math.floor(sampleRate * 0.05) // 50 ms fade in/out

  for (let i = 0; i < numSamples; i++) {
    const t = i / sampleRate

    // Additive synthesis: two sine waves at equal gain
    let sample =
      Math.sin(2 * Math.PI * freq1 * t) * 0.3 +
      Math.sin(2 * Math.PI * freq2 * t) * 0.3

    // Amplitude envelope (avoid clicks)
    let envelope = 1.0
    if (i < fadeLen) {
      envelope = i / fadeLen                    // fade in
    } else if (i > numSamples - fadeLen) {
      envelope = (numSamples - i) / fadeLen     // fade out
    }
    sample *= envelope

    // Clamp and quantize to 16-bit signed integer
    const intSample = Math.max(
      -32768,
      Math.min(32767, Math.round(sample * 32767)),
    )
    view.setInt16(headerSize + i * bytesPerSample, intSample, true)
  }

  // ── Base64-encode the WAV buffer ──────────────────────────
  // String.fromCharCode on each byte guarantees Latin-1 range — btoa safe.
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return 'data:audio/wav;base64,' + btoa(binary)
}

function writeString(view: DataView, offset: number, str: string): void {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i))
  }
}

/** Base64-encoded WAV data URI of a short two-tone notification chime. */
export const CHIME_DATA_URI = generateChimeDataUri()
