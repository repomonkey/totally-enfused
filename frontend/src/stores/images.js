import { writable, derived } from 'svelte/store'

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

  for (const path of paths) {
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
}
