import { TouchTestHarness } from '../harness/test-harness'
import { PhysicalNestSurface } from './components/PhysicalNestSurface'
export default function App() {
  const physical = new URLSearchParams(window.location.search).get('surface') === 'nest'
  return physical ? <PhysicalNestSurface /> : <TouchTestHarness />
}
