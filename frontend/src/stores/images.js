import { writable, derived, get } from 'svelte/store'

export const images = writable([])
// Each image: { path, name, thumbnail, preview, ev, width, height, loading }

export const selectedIndex = writable(0)

export const selectedImage = derived(
  [images, selectedIndex],
  ([$images, $idx]) => $images[$idx] ?? null
)

export function addImages(newImages) {
  images.update(list => {
    const existing = new Set(list.map(i => i.path))
    const toAdd = newImages.filter(img => !existing.has(img.path))
    return [...list, ...toAdd]
  })
}

export function removeImage(path) {
  images.update(list => list.filter(i => i.path !== path))
  selectedIndex.update(idx => Math.max(0, idx - 1))
}

export function reorderImages(from, to) {
  images.update(list => {
    const next = [...list]
    const [item] = next.splice(from, 1)
    next.splice(to, 0, item)
    return next
  })
}

export function clearImages() {
  images.set([])
  selectedIndex.set(0)
}

export function updateImage(path, updates) {
  images.update(list => list.map(img => img.path === path ? { ...img, ...updates } : img))
}

const THUMB_CONCURRENCY = 4  // each pywebview call runs on its own Python thread

async function loadOne(path) {
  try {
    const [info, thumb] = await Promise.all([
      window.pywebview?.api?.get_image_info(path),
      window.pywebview?.api?.get_thumbnail(path),
    ])
    updateImage(path, {
      loading: false,
      thumbnail: thumb ? `data:image/jpeg;base64,${thumb}` : null,
      ev: info?.ev ?? null,
      width: info?.width ?? null,
      height: info?.height ?? null,
    })
  } catch {
    updateImage(path, { loading: false })
  }
}

export async function loadImagePaths(paths) {
  const initial = paths.map(path => ({
    path,
    name: path.split('/').pop(),
    thumbnail: null,
    preview: null,
    ev: null,
    width: null,
    height: null,
    loading: true,
  }))
  addImages(initial)

  const queue = [...paths]
  const worker = async () => { while (queue.length) await loadOne(queue.shift()) }
  await Promise.all(Array.from({ length: Math.min(THUMB_CONCURRENCY, queue.length) }, worker))
}

// Full-size preview for the comparison view, fetched when an image is first
// shown and cached on the image entry.
const previewsInFlight = new Set()

export async function ensurePreview(path) {
  if (!path || previewsInFlight.has(path)) return
  const img = get(images).find(i => i.path === path)
  if (!img || img.preview) return
  previewsInFlight.add(path)
  try {
    const b64 = await window.pywebview?.api?.get_preview(path)
    if (b64) updateImage(path, { preview: `data:image/jpeg;base64,${b64}` })
  } finally {
    previewsInFlight.delete(path)
  }
}
