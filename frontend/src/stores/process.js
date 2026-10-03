import { writable, derived } from 'svelte/store'

export const processState = writable('idle') // idle | running | done | error
export const processProgress = writable(0)    // 0–100
export const processStage = writable('')      // 'align' | 'blend'
export const processMessage = writable('')
export const processError = writable('')
export const resultPath = writable('')
export const resultPreview = writable('')

export const isRunning = derived(processState, s => s === 'running')
export const isDone = derived(processState, s => s === 'done')

export function resetProcess() {
  processState.set('idle')
  processProgress.set(0)
  processStage.set('')
  processMessage.set('')
  processError.set('')
  resultPath.set('')
  resultPreview.set('')
}
