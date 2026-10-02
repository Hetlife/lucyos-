import { useEffect, useRef, useState } from 'react'
import tokens from '../../theme/function-tokens.json'
import { eyeState, outlinePath, pupilFor } from './functionEyeGeometry'

/**
 * The Lucy Nest almond eye, drawn as inline SVG in the native visual language.
 *
 * Decorative motion is optional and disabled for `prefers-reduced-motion` (or
 * when `animate` is false). The eye never encodes real system state: it is
 * presence, not evidence.
 */

const NATIVE_TICK_MS = 80 // ~12.5fps, matching the native home refresh target

export type FunctionEyeProps = {
  /** Half-width of the almond in viewBox units. */
  halfWidth?: number
  /** Half-height of the almond in viewBox units. */
  halfHeight?: number
  /** Fill of the eye body. Defaults to the native ink token. */
  color?: string
  /** Fill of the pupil. Defaults to the native red token. */
  pupilColor?: string
  /** Enable the slow glance/blink. Defaults to true. */
  animate?: boolean
  /** Force a static eye regardless of `animate`. */
  reducedMotion?: boolean
  /** Accessible label. */
  label?: string
}

export function FunctionEye({
  halfWidth = 174,
  halfHeight = 49,
  color = tokens.color.ink,
  pupilColor = tokens.color.red,
  animate = true,
  reducedMotion = false,
  label = 'Lucy presence eye',
}: FunctionEyeProps) {
  const prefersReduced = useReducedMotion()
  const staticEye = !animate || reducedMotion || prefersReduced
  const [tick, setTick] = useState(0)
  const frame = useRef<number | null>(null)

  useEffect(() => {
    if (staticEye) return
    let last = 0
    let start = 0
    const step = (now: number) => {
      if (!start) start = now
      if (now - last >= NATIVE_TICK_MS) {
        last = now
        setTick(now - start)
      }
      frame.current = requestAnimationFrame(step)
    }
    frame.current = requestAnimationFrame(step)
    return () => {
      if (frame.current !== null) cancelAnimationFrame(frame.current)
      frame.current = null
    }
  }, [staticEye])

  const { gaze, openness } = eyeState(tick, { animate: animate && !reducedMotion, reducedMotion: prefersReduced })
  const cx = 240
  const cy = 120
  const openHalfHeight = halfHeight * openness
  const path = outlinePath(cx, cy, halfWidth, Math.max(0.5, openHalfHeight))
  const pupil = pupilFor(cx, cy, Math.max(0.5, openHalfHeight), gaze)

  return (
    <svg
      role="img"
      aria-label={label}
      viewBox="0 0 480 240"
      preserveAspectRatio="xMidYMid meet"
      className="function-eye"
      style={{ width: '100%', height: 'auto', display: 'block' }}
    >
      <path d={path} fill={color} />
      {openness > 0.2 && <circle cx={pupil.cx} cy={pupil.cy} r={pupil.r} fill={pupilColor} />}
    </svg>
  )
}

/** Reads the OS reduced-motion preference; false during SSR. */
function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false)
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const query = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReduced(query.matches)
    update()
    query.addEventListener?.('change', update)
    return () => query.removeEventListener?.('change', update)
  }, [])
  return reduced
}
