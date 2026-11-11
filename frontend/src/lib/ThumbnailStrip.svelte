<script>
  import { images, selectedIndex, removeImage, reorderImages, referencePath, effectiveReference } from '../stores/images.js'
  import { settings } from '../stores/settings.js'
  import DropZone from './DropZone.svelte'

  let dragFrom = $state(null)
  let dragOverIdx = $state(null)

  function select(idx) {
    selectedIndex.set(idx)
  }

  function setReference(e, path) {
    e.stopPropagation()
    referencePath.set($referencePath === path ? null : path)   // clicking the chosen one returns to auto
  }

  function remove(e, path) {
    e.stopPropagation()
    removeImage(path)
  }

  function startDrag(e, idx) {
    dragFrom = idx
    e.dataTransfer.effectAllowed = 'move'
  }

  function onDragOverThumb(e, idx) {
    e.preventDefault()
    dragOverIdx = idx
  }

  function onDropThumb(e, idx) {
    e.preventDefault()
    if (dragFrom !== null && dragFrom !== idx) {
      reorderImages(dragFrom, idx)
      selectedIndex.set(idx)
    }
    dragFrom = null
    dragOverIdx = null
  }

  function onDragEnd() {
    dragFrom = null
    dragOverIdx = null
  }
</script>

<div class="strip">
  {#each $images as img, idx}
    <div
      class="thumb-wrap"
      class:selected={idx === $selectedIndex}
      class:drag-over={dragOverIdx === idx}
      draggable="true"
      role="button"
      tabindex="0"
      aria-label="Image {idx + 1}: {img.name}"
      onclick={() => select(idx)}
      onkeydown={e => e.key === 'Enter' && select(idx)}
      ondragstart={e => startDrag(e, idx)}
      ondragover={e => onDragOverThumb(e, idx)}
      ondrop={e => onDropThumb(e, idx)}
      ondragend={onDragEnd}
    >
      {#if img.thumbnail}
        <img class="thumb" src={img.thumbnail} alt={img.name} draggable="false" />
      {:else if img.loading}
        <div class="thumb thumb-placeholder loading"></div>
      {:else}
        <div class="thumb thumb-placeholder"></div>
      {/if}

      {#if img.ev !== null && img.ev !== undefined}
        <span class="ev-badge">{img.ev > 0 ? '+' : ''}{img.ev.toFixed(1)} EV</span>
      {/if}

      {#if $settings.motion_enabled}
        {#if img.path === $effectiveReference}
          <span class="ref-badge" title="Moving areas come from this frame{$referencePath ? '' : ' (chosen automatically: nearest 0 EV)'}">REF</span>
        {:else}
          <button class="ref-btn" title="Take moving areas from this frame" aria-label="Use {img.name} as the reference for moving areas"
            onclick={e => setReference(e, img.path)}>REF</button>
        {/if}
      {/if}

      <button
        class="remove-btn"
        aria-label="Remove {img.name}"
        onclick={e => remove(e, img.path)}
      >
        <svg viewBox="0 0 12 12" fill="currentColor">
          <path d="M1 1l10 10M11 1L1 11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </button>
    </div>
  {/each}

  <DropZone onFilesAdded={() => {}} />
</div>

<style>
  .strip {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    height: 100%;
    overflow-x: auto;
    overflow-y: hidden;
  }

  .thumb-wrap {
    position: relative;
    flex-shrink: 0;
    width: 88px;
    height: 66px;
    border-radius: var(--radius-sm);
    border: 2px solid transparent;
    cursor: pointer;
    overflow: hidden;
    transition: border-color var(--transition), transform var(--transition);
  }

  .thumb-wrap:hover {
    border-color: var(--text-muted);
    transform: translateY(-1px);
  }

  .thumb-wrap.selected {
    border-color: var(--accent);
  }

  .thumb-wrap.drag-over {
    border-color: var(--accent);
    opacity: 0.7;
  }

  .thumb {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    pointer-events: none;
  }

  .thumb-placeholder {
    background: var(--bg-overlay);
  }

  @keyframes pulse {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 0.8; }
  }

  .loading {
    animation: pulse 1.5s ease infinite;
  }

  .ref-badge, .ref-btn {
    position: absolute;
    top: 3px;
    left: 3px;
    font-family: var(--font-mono);
    font-size: 9px;
    font-weight: 700;
    padding: 0 4px;
    border-radius: 2px;
    line-height: 14px;
  }

  .ref-badge {
    background: var(--accent);
    color: var(--accent-text);
  }

  .ref-btn {
    background: rgba(0, 0, 0, 0.6);
    color: #fff;
    border: none;
    cursor: pointer;
    opacity: 0;
    transition: opacity var(--transition);
  }

  .thumb-wrap:hover .ref-btn,
  .ref-btn:focus-visible {
    opacity: 1;
  }

  .ev-badge {
    position: absolute;
    bottom: 3px;
    left: 3px;
    font-size: 9px;
    font-family: var(--font-mono);
    color: #fff;
    background: rgba(0,0,0,0.6);
    padding: 1px 4px;
    border-radius: 3px;
    letter-spacing: 0.3px;
    pointer-events: none;
  }

  .remove-btn {
    position: absolute;
    top: 2px;
    right: 2px;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: rgba(0,0,0,0.7);
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity var(--transition), color var(--transition);
    padding: 0;
  }

  .thumb-wrap:hover .remove-btn {
    opacity: 1;
  }

  .remove-btn:hover {
    color: var(--error);
  }

  .remove-btn svg {
    width: 8px;
    height: 8px;
  }
</style>
