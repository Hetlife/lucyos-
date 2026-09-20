import { useState } from 'react'
import { RotateCcw, ShieldCheck, Siren, TestTube2, Wrench } from 'lucide-react'
import { TouchInterface, Task, LucyStatus } from '../src/components/TouchInterface'

const baseTasks: Task[] = [
  { id: 'runtime', title: 'Lucy-Nest Runtime', summary: 'Display client and state bridge', status: 'RUNNING', evidenceSteps: 2, totalSteps: 5, logs: ['bridge: connected', 'display: 480x272', 'heartbeat: fresh'] },
  { id: 'renderer', title: 'Presence Renderer', summary: 'Avatar motion and status surfaces', status: 'VERIFYING', evidenceSteps: 4, totalSteps: 6, logs: ['unit: renderer PASS', 'motion: snapshot PASS', 'device: pending visual check'] },
  { id: 'owner-gate', title: 'Deploy Startup Hook', summary: 'Enable Lucy-Nest client at boot with rollback path', status: 'BLOCKED', evidenceSteps: 3, totalSteps: 5, logs: ['rollback: PASS', 'recovery: PASS', 'owner approval: REQUIRED'], critical: true }
]

function patchTask(tasks: Task[], id: string, patch: Partial<Task>) { return tasks.map(t => t.id === id ? { ...t, ...patch } : t) }

export function TouchTestHarness() {
  const [tasks, setTasks] = useState(baseTasks)
  const [approvalTask, setApprovalTask] = useState<Task | null>(null)
  const [lastCommand, setLastCommand] = useState('No command yet')

  const setState = (id: string, status: LucyStatus, evidenceSteps?: number) => setTasks(t => patchTask(t, id, { status, ...(evidenceSteps === undefined ? {} : { evidenceSteps }) }))

  return (
    <div className="harness-shell">
      <TouchInterface
        tasks={tasks}
        approvalTask={approvalTask}
        onCloseApproval={() => setApprovalTask(null)}
        onApprove={id => { setTasks(t => patchTask(t, id, { status: 'VERIFIED', evidenceSteps: 5 })); setApprovalTask(null) }}
        onReject={id => { setTasks(t => patchTask(t, id, { status: 'BLOCKED' })); setApprovalTask(null) }}
        onAvatarCommand={setLastCommand}
      />

      <aside className="harness-panel">
        <div><p className="eyebrow">TOUCH TEST MODE</p><h2>Manual State Harness</h2></div>
        <p className="harness-note">Use these controls to test Lucy-Nest without Mark-2/LucyOS live state.</p>
        <div className="harness-grid">
          <button className="harness-button tactile" onClick={() => setState('runtime', 'BLOCKED')}><Siren size={18} />Worker crash</button>
          <button className="harness-button tactile" onClick={() => setApprovalTask(tasks.find(t => t.id === 'owner-gate') ?? null)}><ShieldCheck size={18} />Owner gate</button>
          <button className="harness-button tactile" onClick={() => setState('renderer', 'VERIFIED', 6)}><TestTube2 size={18} />Passing suite</button>
          <button className="harness-button tactile" onClick={() => setState('runtime', 'RECOVERING', 2)}><Wrench size={18} />Recovery mode</button>
          <button className="harness-button tactile" onClick={() => { setTasks(baseTasks); setApprovalTask(null) }}><RotateCcw size={18} />Reset</button>
        </div>
        <div className="command-readout"><span>Last avatar command</span><strong>{lastCommand}</strong></div>
      </aside>
    </div>
  )
}
