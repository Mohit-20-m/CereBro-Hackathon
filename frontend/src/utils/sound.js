// Tiny Web Audio synth: typing clicks, send pop, receive ding, alert blip.
// No audio files needed. The AudioContext is created on the first user gesture.

let ctx = null
let enabled = true

const getCtx = () => {
  if (!enabled) return null
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext
    if (!AC) return null
    ctx = new AC()
  }
  if (ctx.state === 'suspended') ctx.resume()
  return ctx
}

export const setSoundEnabled = (value) => {
  enabled = value
}

function tone({ freq, to, type = 'sine', dur = 0.12, vol = 0.07, delay = 0 }) {
  const c = getCtx()
  if (!c) return
  const t0 = c.currentTime + delay
  const osc = c.createOscillator()
  const gain = c.createGain()
  osc.type = type
  osc.frequency.setValueAtTime(freq, t0)
  if (to) osc.frequency.exponentialRampToValueAtTime(to, t0 + dur)
  gain.gain.setValueAtTime(0.0001, t0)
  gain.gain.exponentialRampToValueAtTime(vol, t0 + 0.01)
  gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur)
  osc.connect(gain)
  gain.connect(c.destination)
  osc.start(t0)
  osc.stop(t0 + dur + 0.02)
}

function burst({ pitch = 1800, vol = 0.14, len = 0.035 }) {
  const c = getCtx()
  if (!c) return
  const n = Math.floor(c.sampleRate * len)
  const buf = c.createBuffer(1, n, c.sampleRate)
  const data = buf.getChannelData(0)
  for (let i = 0; i < n; i++) data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / n, 3)
  const src = c.createBufferSource()
  src.buffer = buf
  const filter = c.createBiquadFilter()
  filter.type = 'bandpass'
  filter.frequency.value = pitch
  filter.Q.value = 1.1
  const gain = c.createGain()
  gain.gain.value = vol
  src.connect(filter)
  filter.connect(gain)
  gain.connect(c.destination)
  src.start()
}

// Keyboard-style click while typing
export function playKey(kind = 'key') {
  if (kind === 'space') {
    burst({ pitch: 900, vol: 0.2, len: 0.05 })
    tone({ freq: 160, to: 90, type: 'triangle', dur: 0.07, vol: 0.05 })
  } else if (kind === 'back') {
    burst({ pitch: 1200, vol: 0.14, len: 0.04 })
  } else {
    burst({ pitch: 1500 + Math.random() * 1400, vol: 0.14 })
    tone({ freq: 520 + Math.random() * 260, type: 'triangle', dur: 0.04, vol: 0.02 })
  }
}

// Message sent
export function playSend() {
  tone({ freq: 520, to: 780, type: 'sine', dur: 0.12, vol: 0.08 })
  tone({ freq: 780, to: 1040, type: 'sine', dur: 0.14, vol: 0.06, delay: 0.09 })
}

// Message received
export function playReceive() {
  tone({ freq: 880, type: 'sine', dur: 0.14, vol: 0.06 })
  tone({ freq: 660, type: 'sine', dur: 0.2, vol: 0.05, delay: 0.1 })
}

// Gap detected
export function playAlert() {
  tone({ freq: 330, to: 262, type: 'triangle', dur: 0.22, vol: 0.09 })
  tone({ freq: 247, to: 196, type: 'triangle', dur: 0.28, vol: 0.08, delay: 0.16 })
}

// Soft UI click
export function playClick() {
  tone({ freq: 700, to: 500, type: 'sine', dur: 0.06, vol: 0.05 })
}
