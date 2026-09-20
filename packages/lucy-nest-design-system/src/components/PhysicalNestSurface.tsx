import { useEffect, useState } from 'react'

type NestState = { state?: string; headline?: string; detail?: string; progress?: number | null; seq?: number }

export function PhysicalNestSurface() {
  const [live, setLive] = useState<NestState>({ state: 'READY', headline: 'LUCY', detail: 'CONNECTING' })
  const [touch, setTouch] = useState(false)
  useEffect(() => {
    let stop = false
    const poll = async () => {
      try {
        const r = await fetch('/lucy-state', { cache: 'no-store' })
        if (r.ok && !stop) setLive(await r.json())
      } catch {}
    }
    poll(); const id = setInterval(poll, 900)
    return () => { stop = true; clearInterval(id) }
  }, [])
  const state = (live.state || 'READY').toUpperCase()
  return (
    <main className={`nest-device nest-${state.toLowerCase().replace('_','-')} ${touch ? 'nest-touched' : ''}`}
      onPointerDown={() => setTouch(true)} onPointerUp={() => setTimeout(() => setTouch(false), 180)}>
      <header><b>LUCY-NEST</b><span>LIVE · {live.seq ?? 0}</span></header>
      <section className="nest-eye-wrap">
        <div className="nest-rib rib-left" /><div className="nest-eye"><i /><i /></div><div className="nest-rib rib-right" />
      </section>
      <section className="nest-copy"><h1>{state === 'VERIFY' ? 'VERIFYING' : state.replace('_',' ')}</h1><p>{live.detail || live.headline || 'LUCYOS ONLINE'}</p></section>
      <footer><div className="nest-signal"><span /></div><small>EVIDENCE OVER ACTIVITY</small></footer>
    </main>
  )
}
