<script>
  import './styles/global.css'

  import { onMount } from 'svelte'
  import { bridgeReady } from './bridge.js'
  import { images, selectedImage, clearImages, loadImagePaths, ensurePreview } from './stores/images.js'
  import { settings, loadSettings } from './stores/settings.js'
  import {
    processState, processProgress, processStage, processMessage,
    processError, resultPath, resultPreview, resetProcess, doneMessage, isRunning
  } from './stores/process.js'
  import {
    mode, batchSets, batchRun, addToBatch, clearBatch, updateSet, setForRunIndex,
  } from './stores/batch.js'

  import ThumbnailStrip from './lib/ThumbnailStrip.svelte'
  import ComparisonSlider from './lib/ComparisonSlider.svelte'
  import ControlPanel from './lib/ControlPanel.svelte'
  import ProgressBar from './lib/ProgressBar.svelte'
  import ToolStatus from './lib/ToolStatus.svelte'
  import BatchView from './lib/BatchView.svelte'

  let tools = $state(null)
  let resultPreviewData = $state('')

  // Expose for Python to call directly (startup files, URL scheme)
  window.__te_loadFiles = loadImagePaths

  // Bridge: Python → JS events
  window.__te_event = (event, payload) => {
    switch (event) {
      case 'process:start':
        processState.set('running')
        processProgress.set(0)
        break
      case 'process:stage':
        processStage.set(payload.stage)
        processMessage.set(payload.message)
        break
      case 'process:progress':
        if (payload.pct >= 0) processProgress.set(payload.pct)
        processMessage.set(payload.message)
        break
      case 'process:complete':
        processState.set('done')
        processProgress.set(100)
        resultPath.set(payload.output_path)
        resultPreview.set(payload.preview ? `data:image/jpeg;base64,${payload.preview}` : '')
        resultPreviewData = payload.preview ? `data:image/jpeg;base64,${payload.preview}` : ''
        break
      case 'process:error':
        processState.set('error')
        processError.set(payload.message)
        break
      case 'process:cancelled':
        processState.set('cancelled')
        break
      case 'files:open':
        if (!payload.paths?.length) break
        if ($mode === 'batch') addToBatch(payload.paths)
        else loadImagePaths(payload.paths)
        break
      case 'batch:open':
        mode.set('batch')
        addToBatch(payload.paths)
        break
      case 'batch:start':
        batchTotal = payload.total
        processProgress.set(0)
        break
      case 'batch:set_start': {
        const id = setForRunIndex(payload.index)
        updateSet(id, () => ({ status: 'running', pct: 0, message: 'Starting…' }))
        break
      }
      case 'batch:set_progress': {
        const id = setForRunIndex(payload.index)
        updateSet(id, s => ({
          pct: payload.pct >= 0 ? payload.pct : s.pct,
          message: payload.message || s.message,
        }))
        if (payload.pct >= 0) processProgress.set((payload.index + payload.pct / 100) / batchTotal * 100)
        processMessage.set(`Set ${payload.index + 1} of ${batchTotal} — ${payload.message}`)
        break
      }
      case 'batch:set_done': {
        const id = setForRunIndex(payload.index)
        updateSet(id, () => ({
          status: 'done', pct: 100, outputPath: payload.output_path,
          resultThumb: payload.thumbnail ? `data:image/jpeg;base64,${payload.thumbnail}` : null,
        }))
        if (!$resultPath) resultPath.set(payload.output_path)
        break
      }
      case 'batch:set_error':
        updateSet(setForRunIndex(payload.index), () => ({ status: 'error', message: payload.message }))
        break
      case 'batch:complete': {
        // Sets that never started go back to ready
        batchSets.update(list => list.map(s => s.status === 'queued' || s.status === 'running'
          ? { ...s, status: 'ready', pct: 0, message: '' } : s))
        const parts = [`${payload.done} of ${batchTotal} set${batchTotal !== 1 ? 's' : ''} blended`]
        if (payload.failed) parts.push(`${payload.failed} failed`)
        doneMessage.set(parts.join(' · '))
        processProgress.set(100)
        processState.set(payload.cancelled ? 'cancelled' : 'done')
        break
      }
    }
  }

  let batchTotal = 1

  function switchMode(m) {
    if ($isRunning || $mode === m) return
    mode.set(m)
    resetProcess()
  }

  function clearCurrent() {
    if ($mode === 'batch') clearBatch()
    else clearImages()
    resetProcess()
  }

  onMount(async () => {
    // Accept file drops anywhere in the window; Python delivers the paths.
    // Without this, WKWebView navigates to a file dropped outside the drop zone.
    document.addEventListener('dragover', e => e.preventDefault())
    document.addEventListener('drop', e => e.preventDefault())

    await bridgeReady()
    await loadSettings()
    try {
      tools = await window.pywebview.api.check_tools()
    } catch {
      tools = { enfuse: null, align_image_stack: null }
    }
  })

  // Fetch the sharp preview whenever the selection changes (thumbnail shows meanwhile)
  $effect(() => { ensurePreview($selectedImage?.path) })

  const beforeSrc = $derived($selectedImage?.preview ?? $selectedImage?.thumbnail ?? null)
  const afterSrc = $derived($processState === 'done' ? resultPreviewData : null)
  const imageCount = $derived($images.length)
  const hasContent = $derived($mode === 'batch' ? $batchSets.length > 0 : imageCount > 0)
</script>

<div class="app">
  <header class="titlebar">
    <div class="app-name">
      <span class="logo">◑</span>
      <span class="title">Totally Enfused</span>
    </div>
    <div class="mode-switch" role="tablist" aria-label="Mode">
      <button role="tab" aria-selected={$mode === 'single'} class:active={$mode === 'single'}
        disabled={$isRunning} onclick={() => switchMode('single')}>Single</button>
      <button role="tab" aria-selected={$mode === 'batch'} class:active={$mode === 'batch'}
        disabled={$isRunning} onclick={() => switchMode('batch')}>Batch</button>
    </div>
    <div class="header-actions">
      {#if hasContent && !$isRunning}
        <button class="btn-ghost" onclick={clearCurrent}>Clear all</button>
      {/if}
      {#if $mode === 'single' && imageCount > 0}
        <span class="image-count">{imageCount} image{imageCount !== 1 ? 's' : ''}</span>
      {/if}
    </div>
  </header>

  <ToolStatus {tools} />

  <div class="main">
    <div class="preview-area">
      {#if $mode === 'batch'}
        <BatchView />
      {:else}
        <ComparisonSlider
          beforeSrc={beforeSrc}
          afterSrc={afterSrc}
          label="Result"
        />
      {/if}
    </div>

    <ControlPanel {tools} />
  </div>

  {#if $mode === 'single'}
    <div class="filmstrip">
      <ThumbnailStrip />
    </div>
  {/if}

  <ProgressBar />
</div>

<style>
  .app {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
    background: var(--bg-base);
  }

  /* Titlebar */
  .titlebar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 var(--space-5);
    height: 44px;
    flex-shrink: 0;
    background: var(--bg-surface);
    border-bottom: 1px solid var(--border-subtle);
    -webkit-app-region: drag;
  }

  .app-name {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    -webkit-app-region: no-drag;
  }

  .logo {
    font-size: 18px;
    color: var(--accent);
    line-height: 1;
  }

  .title {
    font-size: var(--text-md);
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.01em;
  }

  .mode-switch {
    display: flex;
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 2px;
    -webkit-app-region: no-drag;
  }

  .mode-switch button {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: var(--text-xs);
    padding: 3px 14px;
    border-radius: calc(var(--radius-sm) - 1px);
  }

  .mode-switch button:hover:not(:disabled) { color: var(--text-primary); }

  .mode-switch button.active {
    background: var(--bg-overlay);
    color: var(--text-primary);
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    -webkit-app-region: no-drag;
  }

  .image-count {
    font-size: var(--text-xs);
    color: var(--text-muted);
    font-family: var(--font-mono);
  }

  .btn-ghost {
    background: var(--bg-elevated);
    color: var(--text-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 4px 12px;
    font-size: var(--text-xs);
  }

  .btn-ghost:hover {
    color: var(--text-primary);
    border-color: var(--text-muted);
  }

  /* Layout */
  .main {
    flex: 1;
    display: flex;
    min-height: 0;
    overflow: hidden;
  }

  .preview-area {
    flex: 1;
    min-width: 0;
    padding: var(--space-4);
    display: flex;
    flex-direction: column;
  }

  .filmstrip {
    height: 94px;
    flex-shrink: 0;
    border-top: 1px solid var(--border-subtle);
    background: var(--bg-surface);
  }
</style>
