<script>
  import './styles/global.css'

  import { onMount } from 'svelte'
  import { images, selectedImage, clearImages, loadImagePaths } from './stores/images.js'
  import { settings, loadSettings } from './stores/settings.js'
  import {
    processState, processProgress, processStage, processMessage,
    processError, resultPath, resultPreview, resetProcess
  } from './stores/process.js'

  import ThumbnailStrip from './lib/ThumbnailStrip.svelte'
  import ComparisonSlider from './lib/ComparisonSlider.svelte'
  import ControlPanel from './lib/ControlPanel.svelte'
  import ProgressBar from './lib/ProgressBar.svelte'
  import ToolStatus from './lib/ToolStatus.svelte'

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
      case 'files:open':
        if (payload.paths?.length) loadImagePaths(payload.paths)
        break
    }
  }

  onMount(async () => {
    await loadSettings()
    // Poll until pywebview bridge is ready
    const ready = () => !!window.pywebview?.api
    if (!ready()) {
      await new Promise(resolve => {
        const t = setInterval(() => { if (ready()) { clearInterval(t); resolve() } }, 100)
      })
    }
    const detectTools = async () => {
      try { return await window.pywebview.api.check_tools() }
      catch { return { enfuse: null, align_image_stack: null } }
    }
    tools = await detectTools()
    // Retry once if both are missing — first call can race with cold startup
    if (!tools.enfuse && !tools.align_image_stack) {
      await new Promise(r => setTimeout(r, 1500))
      tools = await detectTools()
    }
  })

  const beforeSrc = $derived($selectedImage?.preview ?? $selectedImage?.thumbnail ?? null)
  const afterSrc = $derived($processState === 'done' ? resultPreviewData : null)
  const imageCount = $derived($images.length)
</script>

<div class="app">
  <header class="titlebar">
    <div class="app-name">
      <span class="logo">◑</span>
      <span class="title">Totally Enfused</span>
    </div>
    <div class="header-actions">
      {#if imageCount > 0}
        <button class="btn-ghost" onclick={() => { clearImages(); resetProcess() }}>
          Clear all
        </button>
        <span class="image-count">{imageCount} image{imageCount !== 1 ? 's' : ''}</span>
      {/if}
    </div>
  </header>

  <ToolStatus {tools} />

  <div class="main">
    <div class="preview-area">
      <ComparisonSlider
        beforeSrc={beforeSrc}
        afterSrc={afterSrc}
        label="Result"
      />
    </div>

    <ControlPanel {tools} />
  </div>

  <div class="filmstrip">
    <ThumbnailStrip />
  </div>

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
