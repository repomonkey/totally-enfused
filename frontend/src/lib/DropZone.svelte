<script>
  import { loadImagePaths } from '../stores/images.js'

  let { onFilesAdded } = $props()

  let dragging = $state(false)
  let dragCounter = 0

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

  // Paths are delivered by Python (pywebview's native drop hook → files:open);
  // WKWebView's File objects don't carry filesystem paths.
  function onDrop(e) {
    e.preventDefault()
    dragging = false
    dragCounter = 0
    onFilesAdded?.()
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
