<script>
  import { loadImagePaths } from '../stores/images.js'

  let { onFilesAdded } = $props()

  let dragging = $state(false)
  let dragCounter = 0

  const SUPPORTED = new Set([
    'image/jpeg', 'image/tiff', 'image/png',
  ])
  const SUPPORTED_EXT = /\.(jpg|jpeg|tif|tiff|png|cr2|cr3|nef|arw|orf|raf|dng|rw2|pef|srw)$/i

  async function processFiles(files) {
    // file.path is Electron-only; pywebview/WKWebView never has it.
    // Fall back to the native file dialog so Python returns real OS paths.
    const hasPath = files.length > 0 && !!files[0].path
    if (hasPath) {
      const paths = Array.from(files)
        .filter(f => f.path && SUPPORTED_EXT.test(f.name))
        .map(f => f.path)
      if (paths.length) { onFilesAdded?.(); await loadImagePaths(paths) }
    } else {
      await openDialog()
    }
  }

  function onDragEnter(e) {
    e.preventDefault()
    dragCounter++
    dragging = true
  }

  function onDragLeave(e) {
    e.preventDefault()
    dragCounter--
    if (dragCounter === 0) dragging = false
  }

  function onDragOver(e) {
    e.preventDefault()
  }

  async function onDrop(e) {
    e.preventDefault()
    dragging = false
    dragCounter = 0
    const files = Array.from(e.dataTransfer.files)
    await processFiles(files)
  }

  async function openDialog() {
    try {
      const paths = await window.pywebview?.api?.open_file_dialog()
      if (paths?.length) await loadImagePaths(paths)
    } catch (err) {
      console.error(err)
    }
  }
</script>

<div
  class="dropzone"
  class:dragging
  role="button"
  tabindex="0"
  aria-label="Drop images here or click to browse"
  ondragenter={onDragEnter}
  ondragleave={onDragLeave}
  ondragover={onDragOver}
  ondrop={onDrop}
  onclick={openDialog}
  onkeydown={e => e.key === 'Enter' && openDialog()}
>
  <div class="inner">
    <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
      <path d="M3 15v4a2 2 0 002 2h14a2 2 0 002-2v-4M7 10l5-5 5 5M12 5v10" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    <p class="label">Drop bracketed exposures here</p>
    <p class="hint">or <span class="link">click to browse</span> — JPG, TIFF, PNG, RAW</p>
  </div>
</div>

<style>
  .dropzone {
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1.5px dashed var(--border);
    border-radius: var(--radius-md);
    padding: var(--space-5) var(--space-6);
    cursor: pointer;
    transition: border-color var(--transition), background var(--transition);
    min-width: 180px;
    flex-shrink: 0;
  }

  .dropzone:hover, .dropzone:focus-visible {
    border-color: var(--accent);
    background: var(--accent-dim);
    outline: none;
  }

  .dropzone.dragging {
    border-color: var(--accent);
    background: var(--accent-dim);
  }

  .inner {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-2);
    pointer-events: none;
  }

  .icon {
    width: 28px;
    height: 28px;
    color: var(--text-muted);
  }

  .dragging .icon {
    color: var(--accent);
  }

  .label {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    font-weight: 500;
  }

  .hint {
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .link {
    color: var(--accent);
  }
</style>
