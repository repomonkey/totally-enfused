<script>
  let { beforeSrc, afterSrc, label = 'Result' } = $props()

  let container = $state(null)
  let sliderX = $state(50) // percent
  let dragging = $state(false)

  function onMouseDown(e) {
    dragging = true
    updateSlider(e.clientX)
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
  }

  function onMouseMove(e) {
    if (dragging) updateSlider(e.clientX)
  }

  function onMouseUp() {
    dragging = false
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
  }

  function updateSlider(clientX) {
    if (!container) return
    const rect = container.getBoundingClientRect()
    const x = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
    sliderX = x * 100
  }
</script>

<div class="comparison" bind:this={container}>
  {#if afterSrc}
    <img class="img after" src={afterSrc} alt={label} draggable="false" />
    <div class="clip before-clip" style="clip-path: inset(0 {100 - sliderX}% 0 0)">
      <img class="img before" src={beforeSrc} alt="Original" draggable="false" />
      <span class="label before-label">Before</span>
    </div>
    <span class="label after-label">{label}</span>
    <div
      class="handle"
      style="left: {sliderX}%"
      role="slider"
      aria-valuenow={Math.round(sliderX)}
      aria-valuemin="0"
      aria-valuemax="100"
      tabindex="0"
      onmousedown={onMouseDown}
    >
      <div class="line"></div>
      <div class="knob">
        <svg viewBox="0 0 16 16" fill="currentColor">
          <path d="M5 8l3-3 3 3M5 8l3 3 3-3" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
    </div>
  {:else if beforeSrc}
    <img class="img" src={beforeSrc} alt="Original" draggable="false" />
    <span class="label after-label">Select image</span>
  {:else}
    <div class="empty">
      <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.2">
        <rect x="6" y="10" width="36" height="28" rx="3" stroke-dasharray="4 3"/>
        <circle cx="17" cy="20" r="4"/>
        <path d="M6 30l10-8 8 6 6-5 12 9" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <p>Load images to see a preview</p>
    </div>
  {/if}
</div>

<style>
  .comparison {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
    border-radius: var(--radius-md);
    background: var(--bg-base);
    cursor: crosshair;
  }

  .img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: contain;
    pointer-events: none;
  }

  .before-clip {
    position: absolute;
    inset: 0;
  }

  .label {
    position: absolute;
    top: var(--space-3);
    font-size: var(--text-xs);
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #fff;
    background: rgba(0,0,0,0.5);
    padding: 3px 8px;
    border-radius: var(--radius-sm);
    pointer-events: none;
  }

  .before-label { left: var(--space-3); }
  .after-label { right: var(--space-3); }

  .handle {
    position: absolute;
    top: 0;
    bottom: 0;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    cursor: col-resize;
    z-index: 10;
  }

  .line {
    position: absolute;
    top: 0; bottom: 0;
    width: 2px;
    background: rgba(255,255,255,0.6);
    left: 50%;
    transform: translateX(-50%);
  }

  .knob {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: white;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: var(--shadow-md);
    color: #333;
  }

  .knob svg {
    width: 16px;
    height: 16px;
  }

  .empty {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--space-4);
    color: var(--text-muted);
  }

  .empty svg {
    width: 64px;
    height: 64px;
    opacity: 0.4;
  }

  .empty p {
    font-size: var(--text-sm);
    color: var(--text-muted);
  }
</style>
