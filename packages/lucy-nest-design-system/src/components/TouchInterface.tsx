import { useMemo, useRef, useState } from 'react'
import { Check, ChevronDown, ChevronUp, Mic, X, AlertTriangle, RotateCcw } from 'lucide-react'
import tokens from '../../theme/tokens.json'
import motion from '../../theme/motion.json'

export type LucyStatus = 'RUNNING' | 'VERIFYING' | 'VERIFIED' | 'BLOCKED' | 'RECOVERING'
export type Task = {
  id: string
  title: string
  summary: string
  status: LucyStatus
  evidenceSteps: number
  totalSteps: number
  logs: string[]
  critical?: boolean
}

type Props = {
  tasks: Task[]
  activeTaskId?: string
  onApprove?: (id: string) => void
  onReject?: (id: string) => void
  approvalTask?: Task | null
  onAvatarCommand?: (text: string) => void
  onCloseApproval?: () => void
}

const STATUS_LABELS: LucyStatus[] = ['RUNNING', 'VERIFYING', 'VERIFIED', 'BLOCKED', 'RECOVERING']

function statusClass(status: LucyStatus) {
  return `status status-${status.toLowerCase()}`
}

function SegmentedProgress({ verified, total, status }: { verified: number; total: number; status: LucyStatus }) {
  return (
    <div className="segmented-progress" aria-label={`${verified} of ${total} evidence steps verified`}>
      {Array.from({ length: total }).map((_, i) => (
        <span key={i} className={`segment ${i < verified ? 'segment-filled' : ''} ${status === 'BLOCKED' ? 'segment-blocked' : ''}`} />
      ))}
    </div>
  )
}

function SwipeConfirm({ onConfirm }: { onConfirm: () => void }) {
  const trackRef = useRef<HTMLDivElement>(null)
  const [dragX, setDragX] = useState(0)
  const [dragging, setDragging] = useState(false)

  const clamp = (x: number) => Math.max(0, Math.min(x, 226))
  const move = (clientX: number) => {
    const left = trackRef.current?.getBoundingClientRect().left ?? 0
    setDragX(clamp(clientX - left - 26))
  }
  const release = () => {
    setDragging(false)
    if (dragX > 180) onConfirm()
    setDragX(0)
  }

  return (
    <div className="swipe-track" ref={trackRef}>
      <span className="swipe-label">SWIPE TO CONFIRM</span>
      <button
        className={`swipe-thumb tactile ${dragging ? 'dragging' : ''}`}
        style={{ transform: `translateX(${dragX}px)` }}
        onPointerDown={(e) => { setDragging(true); e.currentTarget.setPointerCapture(e.pointerId); move(e.clientX) }}
        onPointerMove={(e) => dragging && move(e.clientX)}
        onPointerUp={release}
        onPointerCancel={release}
        aria-label="Swipe right to confirm"
      ><ChevronDown size={18} /></button>
    </div>
  )
}

export function TouchInterface({ tasks, approvalTask, onApprove, onReject, onAvatarCommand, onCloseApproval }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null)
  const [commandOpen, setCommandOpen] = useState(false)
  const [command, setCommand] = useState('')
  const running = useMemo(() => tasks.find(t => t.status === 'RUNNING' || t.status === 'VERIFYING'), [tasks])

  const submitCommand = () => {
    const clean = command.trim()
    if (!clean) return
    onAvatarCommand?.(clean)
    setCommand('')
    setCommandOpen(false)
  }

  return (
    <main className="lucy-surface" style={{
      ['--surface' as string]: tokens.color.surface.dark,
      ['--chassis' as string]: tokens.color.surface.chassis,
      ['--accent' as string]: tokens.color.accent.primary,
      ['--verified' as string]: tokens.color.accent.verified,
      ['--blocked' as string]: tokens.color.accent.blocked,
      ['--muted' as string]: tokens.color.text.muted,
      ['--spring' as string]: motion.motion.bar_fill.easing,
      ['--transition' as string]: motion.motion.bar_fill.duration,
      ['--pulse' as string]: motion.motion.avatar_pulse.duration,
    }}>
      <header className="topbar">
        <div><p className="eyebrow">LUCY-NEST</p><h1>{running ? running.status : 'STANDBY'}</h1></div>
        <button className="avatar tactile" onClick={() => setCommandOpen(true)} aria-label="Open Lucy command input">
          <span className="avatar-eye"><span /><span /></span>
        </button>
      </header>

      <section className="status-strip" aria-label="Lucy system states">
        {STATUS_LABELS.map(s => <span key={s} className={tasks.some(t => t.status === s) ? statusClass(s) : 'status status-inactive'}>{s}</span>)}
      </section>

      <section className="task-stack">
        {tasks.map(task => {
          const isOpen = expanded === task.id
          return (
            <article key={task.id} className={`task-card ${task.status === 'BLOCKED' ? 'task-card-blocked' : ''}`}>
              <button className="task-hit tactile" onClick={() => setExpanded(isOpen ? null : task.id)} aria-expanded={isOpen}>
                <div className="task-copy">
                  <div className="task-title-row"><h2>{task.title}</h2><span className={statusClass(task.status)}>{task.status}</span></div>
                  <p>{task.summary}</p>
                  <SegmentedProgress verified={task.evidenceSteps} total={task.totalSteps} status={task.status} />
                </div>
                {isOpen ? <ChevronUp size={24} /> : <ChevronDown size={24} />}
              </button>
              <div className={`task-details ${isOpen ? 'task-details-open' : ''}`}>
                <div className="log-panel">
                  {task.logs.map((line, i) => <code key={i}>{line}</code>)}
                </div>
              </div>
            </article>
          )
        })}
      </section>

      {approvalTask && (
        <div className="modal-backdrop" role="presentation">
          <section className="approval-modal" role="dialog" aria-modal="true" aria-labelledby="approval-title">
            <div className="modal-head">
              <div><p className="eyebrow">OWNER GATE</p><h2 id="approval-title">{approvalTask.title}</h2></div>
              <button className="icon-button tactile" onClick={onCloseApproval} aria-label="Close approval"><X size={22} /></button>
            </div>
            <p className="modal-copy">{approvalTask.summary}</p>
            <div className="risk-row"><AlertTriangle size={18} /><span>{approvalTask.critical ? 'CRITICAL ACTION — confirmation required' : 'Review evidence before approval'}</span></div>
            {approvalTask.critical && <SwipeConfirm onConfirm={() => onApprove?.(approvalTask.id)} />}
            <div className="approval-actions">
              <button className="decision reject tactile" onClick={() => onReject?.(approvalTask.id)}><X size={20} />REJECT</button>
              <button className="decision approve tactile" onClick={() => onApprove?.(approvalTask.id)}><Check size={20} />APPROVE</button>
            </div>
          </section>
        </div>
      )}

      {commandOpen && (
        <div className="command-overlay" role="dialog" aria-modal="true" aria-label="Lucy command input">
          <button className="command-dismiss" onClick={() => setCommandOpen(false)} aria-label="Close command surface" />
          <div className="command-card">
            <div className="command-avatar"><span className="avatar-eye"><span /><span /></span></div>
            <p className="eyebrow">DIRECT COMMAND</p>
            <textarea autoFocus value={command} onChange={e => setCommand(e.target.value)} placeholder="Tell Lucy what to do…" />
            <div className="command-actions">
              <button className="icon-button tactile" aria-label="Voice command"><Mic size={22} /></button>
              <button className="send-command tactile" onClick={submitCommand}>SEND</button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
