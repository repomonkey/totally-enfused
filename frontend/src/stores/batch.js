import { writable, get } from 'svelte/store'

export const mode = writable('single')        // 'single' | 'batch'
export const batchSources = writable([])      // folders/files the user added
export const framesPerSet = writable(0)       // 0 = auto-detect
export const scanning = writable(false)
export const batchSingles = writable([])      // frames not in any bracket
// Each set: { id, paths, evs, thumbs, include, status, pct, message, outputPath, resultThumb }
// status: 'ready' | 'queued' | 'running' | 'done' | 'error'
export const batchSets = writable([])
// ids of the sets sent to the backend, in order; batch:* event indexes refer to this
export const batchRun = writable([])

let scanToken = 0

export async function addToBatch(paths) {
  batchSources.update(s => [...new Set([...s, ...paths])])
  await rescanBatch()
}

export function clearBatch() {
  scanToken++
  batchSources.set([])
  batchSets.set([])
  batchSingles.set([])
  batchRun.set([])
}

export async function rescanBatch() {
  const token = ++scanToken
  const sources = get(batchSources)
  if (!sources.length) return
  scanning.set(true)
  try {
    const res = await window.pywebview?.api?.scan_batch(sources, get(framesPerSet) || null)
    if (token !== scanToken || !res) return
    batchSets.set(res.sets.map((s, i) => ({
      id: `${i}:${s.paths[0]}`,
      paths: s.paths,
      evs: s.evs,
      thumbs: s.paths.map(() => null),
      include: true,
      status: 'ready',
      pct: 0,
      message: '',
      outputPath: null,
      resultThumb: null,
    })))
    batchSingles.set(res.singles)
  } finally {
    if (token === scanToken) scanning.set(false)
  }
  loadThumbs(token)
}

async function loadThumbs(token) {
  const jobs = get(batchSets).flatMap(s => s.paths.map((p, j) => [s.id, j, p]))
  const worker = async () => {
    while (jobs.length && token === scanToken) {
      const [id, j, path] = jobs.shift()
      const b64 = await window.pywebview?.api?.get_thumbnail(path).catch(() => null)
      if (b64 && token === scanToken) {
        updateSet(id, s => {
          const thumbs = [...s.thumbs]
          thumbs[j] = `data:image/jpeg;base64,${b64}`
          return { thumbs }
        })
      }
    }
  }
  await Promise.all([1, 2, 3, 4].map(worker))
}

export function updateSet(id, fn) {
  batchSets.update(list => list.map(s => (s.id === id ? { ...s, ...fn(s) } : s)))
}

export function setForRunIndex(index) {
  return get(batchRun)[index]
}
