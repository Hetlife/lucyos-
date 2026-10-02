import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

import {
  DEFAULT_PERIOD_MS,
  clamp,
  eyeOutline,
  eyeState,
  gazeFor,
  isBlinking,
  outlinePath,
  pupilFor,
} from '../src/components/functionEyeGeometry.ts'

const here = dirname(fileURLToPath(import.meta.url))
const tokens = JSON.parse(readFileSync(join(here, '..', 'theme', 'function-tokens.json'), 'utf8'))

// --- contrast (WCAG relative luminance), independent of the token file --------
function toLinear(channel) {
  const c = channel / 255
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
}
function luminance(hex) {
  const [r, g, b] = hex.replace('#', '').match(/../g).map(h => parseInt(h, 16))
  return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b)
}
function contrast(fg, bg) {
  const a = luminance(fg)
  const b = luminance(bg)
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)
}

test('the contrast checker itself distinguishes known pass and fail', () => {
  // Positive/negative controls so a broken checker cannot silently pass everything.
  assert.ok(contrast('#ffffff', '#000000') > 20)
  assert.ok(contrast('#f2efe6', '#f20710') < 4.5)
})

test('every declared contrast pair matches its expected outcome (unrounded)', () => {
  const minimum = tokens.contrast.normal_text_min
  for (const pair of tokens.contrast.pairs) {
    const ratio = contrast(pair.foreground, pair.background)
    const passes = ratio >= minimum
    assert.equal(passes, pair.expected === 'pass', `${pair.name} ratio=${ratio}`)
  }
})

test('the negative control really is the off-white-on-red failure', () => {
  const control = tokens.contrast.pairs.find(p => p.expected === 'fail')
  assert.ok(control, 'expected a negative-control pair')
  assert.equal(control.foreground, '#f2efe6')
  assert.equal(control.background, '#f20710')
})

test('tokens expose the native identity values and product touch target', () => {
  assert.equal(tokens.color.red, '#f20710')
  assert.equal(tokens.color.ink, '#100706')
  assert.equal(tokens.color.background, '#090a09')
  assert.equal(tokens.touch_target_px, 48)
})

// --- geometry and motion ------------------------------------------------------

test('a fresh eye is fully open and centred', () => {
  assert.deepEqual(eyeState(0), { gaze: 0, openness: 1 })
})

test('reduced motion is always fully open with no gaze', () => {
  for (const tick of [0, 900, DEFAULT_PERIOD_MS / 2, DEFAULT_PERIOD_MS - 20]) {
    assert.deepEqual(eyeState(tick, { reducedMotion: true }), { gaze: 0, openness: 1 })
    assert.deepEqual(eyeState(tick, { animate: false }), { gaze: 0, openness: 1 })
  }
})

test('the eye blinks only in the brief closed phase', () => {
  const period = DEFAULT_PERIOD_MS
  const blink = tokens.motion.blink_ms
  assert.equal(isBlinking(0, period, blink), false)
  assert.equal(isBlinking(period / 2, period, blink), false)
  assert.equal(isBlinking(period - blink / 2, period, blink), true)
  assert.ok(eyeState(period - blink / 2).openness < 0.2)
})

test('gaze stays within the amplitude and sweeps both directions', () => {
  const amplitude = 40
  let sawNegative = false
  let sawPositive = false
  for (let tick = 0; tick <= DEFAULT_PERIOD_MS; tick += 50) {
    const { gaze } = eyeState(tick, { amplitude })
    assert.ok(Math.abs(gaze) <= amplitude, `gaze ${gaze} out of range`)
    if (gaze < -1) sawNegative = true
    if (gaze > 1) sawPositive = true
  }
  assert.ok(sawNegative && sawPositive, 'gaze should sweep both directions')
})

test('gaze and blink handle negative and huge ticks without NaN', () => {
  for (const tick of [-5000, -1, 0, 10 ** 9, Number.NaN]) {
    const { gaze, openness } = eyeState(tick)
    assert.ok(Number.isFinite(gaze), `gaze not finite at ${tick}`)
    assert.ok(Number.isFinite(openness) && openness >= 0 && openness <= 1)
  }
})

test('clamp and gazeFor are defensive', () => {
  assert.equal(clamp(5, 0, 1), 1)
  assert.equal(clamp(-5, 0, 1), 0)
  assert.equal(clamp(Number.NaN, 2, 3), 2)
  assert.equal(gazeFor(123, 0), 0)
})

test('the almond outline is closed, symmetric in width, and non-empty', () => {
  const { upper, lower } = eyeOutline(240, 120, 174, 49, 16)
  assert.equal(upper.length, 17)
  assert.equal(lower.length, 17)
  assert.ok(upper[0].x < upper[upper.length - 1].x, 'upper runs left to right')
  const path = outlinePath(240, 120, 174, 49, 16)
  assert.ok(path.startsWith('M') && path.endsWith('Z'))
  assert.ok(!path.includes('NaN'))
})

test('the pupil stays inside the eye and scales with opening', () => {
  const open = pupilFor(240, 120, 49, 0)
  const closed = pupilFor(240, 120, 2, 0)
  assert.ok(open.r >= 5 && open.r <= 33)
  assert.ok(closed.r >= 5)
  const shifted = pupilFor(240, 120, 49, 30)
  assert.equal(shifted.cx, 270)
})
