/**
 * Pure geometry and motion for the Lucy Nest almond eye.
 *
 * Kept free of React and the DOM so it can be tested directly by Node's
 * built-in test runner. Node strips TypeScript types but cannot load `.tsx`,
 * so the rendering component (`FunctionEye.tsx`) imports these helpers and the
 * tests import this module. No JSX and no third-party dependency live here.
 */

export type EyeState = {
  /** Horizontal pupil offset in pixels, within [-amplitude, amplitude]. */
  gaze: number
  /** Eyelid opening as a fraction, 0 (closed) .. 1 (fully open). */
  openness: number
}

export type MotionOptions = {
  /** When false, or when reduced motion is requested, the eye is static. */
  animate?: boolean
  reducedMotion?: boolean
  /** Length of one full glance+blink cycle. */
  periodMs?: number
  /** Maximum horizontal pupil travel. */
  amplitude?: number
  /** Duration of the closed phase at the end of each cycle. */
  blinkMs?: number
}

export const DEFAULT_PERIOD_MS = 7200
export const DEFAULT_AMPLITUDE = 40
export const DEFAULT_BLINK_MS = 160

export function clamp(value: number, min: number, max: number): number {
  if (Number.isNaN(value)) return min
  return Math.min(max, Math.max(min, value))
}

/**
 * Whether the eye is in its brief closed phase. The blink occupies the final
 * `blinkMs` of each period so a fresh mount (tick 0) starts fully open.
 */
export function isBlinking(tickMs: number, periodMs = DEFAULT_PERIOD_MS, blinkMs = DEFAULT_BLINK_MS): boolean {
  if (periodMs <= 0 || blinkMs <= 0) return false
  const phase = ((tickMs % periodMs) + periodMs) % periodMs
  return phase > periodMs - blinkMs
}

export function gazeFor(tickMs: number, periodMs = DEFAULT_PERIOD_MS, amplitude = DEFAULT_AMPLITUDE): number {
  if (periodMs <= 0) return 0
  const phase = ((tickMs % periodMs) + periodMs) % periodMs
  const raw = Math.sin((phase / periodMs) * Math.PI * 2) * amplitude
  return clamp(raw, -amplitude, amplitude)
}

/**
 * Resolve gaze and eyelid opening for a moment in time.
 *
 * A static eye (animation off or reduced motion requested) is always fully
 * open with no gaze offset, so decorative motion never implies real state.
 */
export function eyeState(tickMs: number, options: MotionOptions = {}): EyeState {
  const {
    animate = true,
    reducedMotion = false,
    periodMs = DEFAULT_PERIOD_MS,
    amplitude = DEFAULT_AMPLITUDE,
    blinkMs = DEFAULT_BLINK_MS,
  } = options
  if (!animate || reducedMotion) return { gaze: 0, openness: 1 }
  const openness = isBlinking(tickMs, periodMs, blinkMs) ? 0.06 : 1
  return { gaze: gazeFor(tickMs, periodMs, amplitude), openness }
}

export type Point = { x: number; y: number }

/**
 * Almond outline as an upper and lower polyline, mirroring the native renderer:
 * a sine arch across the width, with a slight downward tilt to the right.
 */
export function eyeOutline(cx: number, cy: number, halfWidth: number, halfHeight: number, steps = 64): { upper: Point[]; lower: Point[] } {
  const upper: Point[] = []
  const lower: Point[] = []
  const count = Math.max(2, Math.floor(steps))
  for (let i = 0; i <= count; i++) {
    const u = i / count
    const x = cx - halfWidth + 2 * halfWidth * u
    const curve = Math.pow(Math.sin(Math.PI * u), 0.85)
    const tilt = (u - 0.5) * 8
    upper.push({ x, y: cy - halfHeight * curve + tilt })
    lower.push({ x, y: cy + halfHeight * 0.88 * curve + tilt })
  }
  return { upper, lower }
}

export type Pupil = { cx: number; cy: number; r: number }

export function pupilFor(cx: number, cy: number, halfHeight: number, gaze: number): Pupil {
  const r = clamp(halfHeight * 0.68, 5, 33)
  return { cx: cx + gaze, cy: cy - halfHeight * 0.3, r }
}

/** SVG path string for the almond outline (upper left-to-right, lower right-to-left). */
export function outlinePath(cx: number, cy: number, halfWidth: number, halfHeight: number, steps = 64): string {
  const { upper, lower } = eyeOutline(cx, cy, halfWidth, halfHeight, steps)
  const points = [...upper, ...[...lower].reverse()]
  return points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(' ') + ' Z'
}
