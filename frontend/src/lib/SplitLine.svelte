<script>
  // Draggable sky / foreground line drawn over the preview image.
  // Positions are fractions of the image, matching backend/split.py.
  import { settings } from '../stores/settings.js'

  let { src } = $props()

  let cw = $state(0)
  let ch = $state(0)
  let natural = $state(null)   // { w, h } of the shown image
  let dragging = $state(false)
  let el = $state(null)

  $effect(() => {
    if (!src) { natural = null; return }
    const img = new Image()
    img.onload = () => { natural = { w: img.naturalWidth, h: img.naturalHeight } }
    img.src = src
  })

  // Where object-fit: contain puts the image inside the container
  const rect = $derived.by(() => {
    if (!natural || !cw || !ch) return null
    const scale = Math.min(cw / natural.w, ch / natural.h)
    const w = natural.w * scale, h = natural.h * scale
    return { left: (cw - w) / 2, top: (ch - h) / 2, w, h }
  })

  const tan = $derived(Math.tan($settings.split_tilt * Math.PI / 180))
  // Line height at the right edge, where the grip sits
  const gripY = $derived(rect ? $settings.split_line * rect.h + rect.w / 2 * tan : 0)

  function setFromPointer(e) {
    const box = el.getBoundingClientRect()
    const x = e.clientX - box.left, y = e.clientY - box.top
    const line = (y - (x - rect.w / 2) * tan) / rect.h
    settings.update(s => ({ ...s, split_line: Math.round(Math.max(0.05, Math.min(0.95, line)) * 1000) / 1000 }))
  }

  function down(e) {
    dragging = true
    e.currentTarget.setPointerCapture(e.pointerId)
    e.preventDefault()
  }
  function move(e) { if (dragging) setFromPointer(e) }
  function up() { dragging = false }
</script>

<div class="overlay" bind:clientWidth={cw} bind:clientHeight={ch}>
  {#if rect}
    <div class="area" bind:this={el}
      style="left:{rect.left}px; top:{rect.top}px; width:{rect.w}px; height:{rect.h}px">
      <div class="band" style="top:{$settings.split_line * 100}%; height:{Math.max($settings.split_feather * 100, 0.2)}%;
        transform: translateY(-50%) rotate({$settings.split_tilt}deg)"></div>
      <div class="line" class:dragging role="slider" tabindex="-1"
        aria-label="Sky line" aria-valuenow={Math.round($settings.split_line * 100)}
        style="top:{$settings.split_line * 100}%; transform: translateY(-50%) rotate({$settings.split_tilt}deg)"
        onpointerdown={down} onpointermove={move} onpointerup={up} onpointercancel={up}>
        <div class="stroke"></div>
      </div>
      <div class="grip" class:dragging style="top:{gripY}px"
        onpointerdown={down} onpointermove={move} onpointerup={up} onpointercancel={up}>
        <span>Sky</span><span>Foreground</span>
      </div>
    </div>
  {/if}
</div>

<style>
  .overlay {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }

  .area {
    position: absolute;
    overflow: hidden;
  }

  .band, .line {
    position: absolute;
    left: -25%;
    width: 150%;
    transform-origin: center center;
  }

  .band {
    background: linear-gradient(to bottom, rgba(120, 170, 255, 0.16), rgba(255, 190, 120, 0.12));
    border-top: 1px dashed rgba(255, 255, 255, 0.25);
    border-bottom: 1px dashed rgba(255, 255, 255, 0.25);
    box-sizing: border-box;
  }

  .line {
    height: 14px;
    cursor: row-resize;
    pointer-events: auto;
    z-index: 11;
  }

  .stroke {
    position: absolute;
    top: 50%;
    left: 0; right: 0;
    height: 0;
    border-top: 1.5px solid rgba(255, 255, 255, 0.75);
    box-shadow: 0 0 2px rgba(0, 0, 0, 0.6);
  }

  .line:hover .stroke, .line.dragging .stroke { border-top-color: var(--accent); }

  .grip {
    position: absolute;
    right: 6px;
    transform: translateY(-50%);
    display: flex;
    flex-direction: column;
    gap: 6px;
    align-items: flex-end;
    cursor: row-resize;
    pointer-events: auto;
    z-index: 12;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #fff;
  }

  .grip span {
    background: rgba(0, 0, 0, 0.55);
    padding: 2px 6px;
    border-radius: var(--radius-sm);
  }

  .grip:hover span, .grip.dragging span { background: var(--accent); color: var(--accent-text); }
</style>
