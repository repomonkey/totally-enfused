<script>
  import { settings, saveSettings, applyPreset } from '../stores/settings.js'
  import { images } from '../stores/images.js'
  import {
    processState, processProgress, processStage, processMessage,
    processError, resultPath, resultPreview, resetProcess, isRunning
  } from '../stores/process.js'

  let { tools, onResult } = $props()

  let presets = $state({})
  let openSection = $state('align')
  let customPresetName = $state('')
  let showPresetSave = $state(false)

  $effect(() => {
    window.pywebview?.api?.get_presets().then(p => { presets = p ?? {} })
  })

  function toggleSection(id) {
    openSection = openSection === id ? null : id
  }

  async function pickOutputDir() {
    const dir = await window.pywebview?.api?.open_folder_dialog()
    if (dir) settings.update(s => ({ ...s, output_dir: dir }))
  }

  function formatSliderValue(key) {
    return $settings[key]?.toFixed(2) ?? '—'
  }

  function buildOutputPath() {
    const imgs = $images
    if (!imgs.length) return null
    const first = imgs[0].path
    const dir = $settings.output_dir_mode === 'custom' && $settings.output_dir
      ? $settings.output_dir
      : first.substring(0, first.lastIndexOf('/'))
    const baseName = first.split('/').pop().replace(/\.[^.]+$/, '')
    const ext = $settings.output_format === 'jpeg' ? 'jpg'
      : $settings.output_format === 'tiff' ? 'tif'
      : $settings.output_format
    const filename = $settings.output_template
      .replace('{name}', baseName)
      .replace('{ext}', ext)
    return `${dir}/${filename}`
  }

  async function runProcess() {
    if ($isRunning) return
    const paths = $images.map(i => i.path)
    if (paths.length < 2) return

    const outputPath = buildOutputPath()
    if (!outputPath) return

    resetProcess()
    processState.set('running')

    await saveSettings($settings)

    await window.pywebview?.api?.process({
      input_paths: paths,
      output_path: outputPath,
      align_enabled: $settings.align_enabled,
      align_mode: $settings.align_mode,
      align_grid_points: $settings.align_grid_points,
      align_crop: $settings.align_crop,
      exposure_weight: $settings.fusion_exposure_weight,
      saturation_weight: $settings.fusion_saturation_weight,
      contrast_weight: $settings.fusion_contrast_weight,
      hard_mask: $settings.fusion_hard_mask,
      levels: $settings.fusion_levels,
    })
  }

  async function saveCurrentPreset() {
    if (!customPresetName.trim()) return
    const key = customPresetName.toLowerCase().replace(/\s+/g, '_')
    const preset = {
      name: customPresetName,
      description: 'Custom preset',
      exposure_weight: $settings.fusion_exposure_weight,
      saturation_weight: $settings.fusion_saturation_weight,
      contrast_weight: $settings.fusion_contrast_weight,
      hard_mask: $settings.fusion_hard_mask,
      levels: $settings.fusion_levels,
    }
    await window.pywebview?.api?.save_preset(key, preset)
    presets = { ...presets, [key]: { ...preset, builtin: false } }
    showPresetSave = false
    customPresetName = ''
  }

  const canRun = $derived($images.length >= 2 && !$isRunning)
  const outputPreview = $derived(buildOutputPath())
</script>

<aside class="panel">
  <!-- Presets -->
  <div class="section-wrap">
    <button class="section-header" onclick={() => toggleSection('presets')}>
      <span>Presets</span>
      <svg class="chevron" class:open={openSection === 'presets'} viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
        <path d="M1 1l4 4 4-4"/>
      </svg>
    </button>
    {#if openSection === 'presets'}
    <div class="section-body presets-grid">
      {#each Object.entries(presets) as [key, preset]}
        <button
          class="preset-btn"
          class:active={$settings.last_preset === key}
          onclick={() => { applyPreset(preset); settings.update(s => ({...s, last_preset: key})) }}
        >
          <span class="preset-name">{preset.name}</span>
          <span class="preset-desc">{preset.description}</span>
        </button>
      {/each}

      {#if showPresetSave}
        <div class="preset-save-row">
          <input
            type="text"
            placeholder="Preset name"
            bind:value={customPresetName}
            onkeydown={e => e.key === 'Enter' && saveCurrentPreset()}
          />
          <button class="btn-accent-sm" onclick={saveCurrentPreset}>Save</button>
          <button class="btn-ghost-sm" onclick={() => { showPresetSave = false; customPresetName = '' }}>✕</button>
        </div>
      {:else}
        <button class="preset-btn add-preset" onclick={() => showPresetSave = true}>
          + Save current as preset
        </button>
      {/if}
    </div>
    {/if}
  </div>

  <!-- Alignment -->
  <div class="section-wrap">
    <button class="section-header" onclick={() => toggleSection('align')}>
      <div class="header-left">
        <span>Alignment</span>
        {#if !$settings.align_enabled}
          <span class="badge off">Off</span>
        {/if}
      </div>
      <svg class="chevron" class:open={openSection === 'align'} viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
        <path d="M1 1l4 4 4-4"/>
      </svg>
    </button>
    {#if openSection === 'align'}
    <div class="section-body">
      <label class="toggle-row">
        <input type="checkbox" bind:checked={$settings.align_enabled} />
        <span>Enable alignment</span>
      </label>

      {#if $settings.align_enabled}
        <div class="field">
          <label for="align-mode">Mode</label>
          <select id="align-mode" bind:value={$settings.align_mode}>
            <option value="translation">Translation only (locked tripod)</option>
            <option value="translation_rotation">Translation + rotation (handheld)</option>
            <option value="homography">Full homography (large shifts)</option>
          </select>
        </div>

        <div class="field">
          <label for="grid-pts">Control point grid <span class="val">{$settings.align_grid_points}×{$settings.align_grid_points}</span></label>
          <input id="grid-pts" type="range" min="4" max="16" step="1" bind:value={$settings.align_grid_points} />
        </div>

        <label class="toggle-row">
          <input type="checkbox" bind:checked={$settings.align_crop} />
          <span>Auto-crop aligned output</span>
        </label>
      {/if}
    </div>
    {/if}
  </div>

  <!-- Fusion -->
  <div class="section-wrap">
    <button class="section-header" onclick={() => toggleSection('fusion')}>
      <span>Fusion</span>
      <svg class="chevron" class:open={openSection === 'fusion'} viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
        <path d="M1 1l4 4 4-4"/>
      </svg>
    </button>
    {#if openSection === 'fusion'}
    <div class="section-body">
      <div class="field">
        <label for="fw-exposure">Exposure weight <span class="val">{formatSliderValue('fusion_exposure_weight')}</span></label>
        <input id="fw-exposure" type="range" min="0" max="1" step="0.05" bind:value={$settings.fusion_exposure_weight} />
      </div>

      <div class="field">
        <label for="fw-saturation">Saturation weight <span class="val">{formatSliderValue('fusion_saturation_weight')}</span></label>
        <input id="fw-saturation" type="range" min="0" max="1" step="0.05" bind:value={$settings.fusion_saturation_weight} />
      </div>

      <div class="field">
        <label for="fw-contrast">Contrast weight <span class="val">{formatSliderValue('fusion_contrast_weight')}</span></label>
        <input id="fw-contrast" type="range" min="0" max="1" step="0.05" bind:value={$settings.fusion_contrast_weight} />
      </div>

      <div class="field">
        <label for="fw-levels">Blend levels <span class="val">{$settings.fusion_levels}</span></label>
        <input id="fw-levels" type="range" min="1" max="29" step="1" bind:value={$settings.fusion_levels} />
      </div>

      <label class="toggle-row">
        <input type="checkbox" bind:checked={$settings.fusion_hard_mask} />
        <span>Hard mask</span>
      </label>
    </div>
    {/if}
  </div>

  <!-- Output -->
  <div class="section-wrap">
    <button class="section-header" onclick={() => toggleSection('output')}>
      <span>Output</span>
      <svg class="chevron" class:open={openSection === 'output'} viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
        <path d="M1 1l4 4 4-4"/>
      </svg>
    </button>
    {#if openSection === 'output'}
    <div class="section-body">
      <div class="field">
        <label for="out-format">Format</label>
        <select id="out-format" bind:value={$settings.output_format}>
          <option value="tiff">TIFF 16-bit</option>
          <option value="jpeg">JPEG</option>
          <option value="png">PNG</option>
        </select>
      </div>

      {#if $settings.output_format === 'jpeg'}
        <div class="field">
          <label for="out-quality">Quality <span class="val">{$settings.output_quality}</span></label>
          <input id="out-quality" type="range" min="60" max="100" step="1" bind:value={$settings.output_quality} />
        </div>
      {/if}

      <div class="field">
        <label for="out-dir-mode">Save to</label>
        <select id="out-dir-mode" bind:value={$settings.output_dir_mode}>
          <option value="same_as_input">Same folder as input</option>
          <option value="custom">Custom folder</option>
        </select>
      </div>

      {#if $settings.output_dir_mode === 'custom'}
        <div class="field dir-row">
          <input type="text" readonly value={$settings.output_dir || 'No folder selected'} />
          <button class="btn-ghost-sm" onclick={pickOutputDir}>Browse</button>
        </div>
      {/if}

      <div class="field">
        <label for="out-template">Filename template</label>
        <input type="text" id="out-template" bind:value={$settings.output_template} />
        <span class="hint-text">Use {'{name}'} and {'{ext}'}</span>
      </div>

      {#if outputPreview}
        <p class="output-preview">{outputPreview.split('/').pop()}</p>
      {/if}
    </div>
    {/if}
  </div>

  <div class="run-wrap">
    <button
      class="run-btn"
      disabled={!canRun}
      onclick={runProcess}
    >
      {#if $isRunning}
        <span class="spinner"></span> Processing…
      {:else}
        <svg viewBox="0 0 16 16" fill="currentColor" class="run-icon">
          <path d="M3 2.5l11 5.5-11 5.5V2.5z"/>
        </svg>
        {$images.length < 2 ? 'Load 2+ images' : 'Blend Images'}
      {/if}
    </button>
  </div>
</aside>

<style>
  .panel {
    width: 260px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    background: var(--bg-surface);
    border-left: 1px solid var(--border-subtle);
    overflow-y: auto;
    overflow-x: hidden;
  }

  .section-wrap {
    border-bottom: 1px solid var(--border-subtle);
  }

  .section-header {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-3) var(--space-4);
    background: none;
    color: var(--text-primary);
    font-size: var(--text-sm);
    font-weight: 500;
    text-align: left;
    border-radius: 0;
  }

  .section-header:hover {
    background: var(--bg-elevated);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }

  .chevron {
    width: 10px;
    height: 6px;
    color: var(--text-muted);
    transition: transform var(--transition);
  }

  .chevron.open {
    transform: rotate(180deg);
  }

  .badge {
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 1px 5px;
    border-radius: 3px;
    background: var(--bg-overlay);
    color: var(--text-muted);
  }

  .section-body {
    padding: var(--space-2) var(--space-4) var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .field label {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .val {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--accent);
  }

  select, input[type="text"] {
    width: 100%;
  }

  .toggle-row {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    cursor: pointer;
    color: var(--text-secondary);
    font-size: var(--text-sm);
  }

  .toggle-row input[type="checkbox"] {
    accent-color: var(--accent);
    width: 14px;
    height: 14px;
    cursor: pointer;
  }

  .dir-row {
    flex-direction: row;
    gap: var(--space-2);
  }

  .dir-row input {
    flex: 1;
    min-width: 0;
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .hint-text {
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .output-preview {
    font-size: var(--text-xs);
    font-family: var(--font-mono);
    color: var(--text-muted);
    background: var(--bg-overlay);
    padding: 4px 8px;
    border-radius: var(--radius-sm);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Presets */
  .presets-grid {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .preset-btn {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    padding: var(--space-2) var(--space-3);
    background: var(--bg-elevated);
    border-radius: var(--radius-sm);
    border: 1px solid transparent;
    color: var(--text-secondary);
    font-size: var(--text-sm);
    text-align: left;
    transition: border-color var(--transition), background var(--transition);
  }

  .preset-btn:hover {
    background: var(--bg-overlay);
    color: var(--text-primary);
  }

  .preset-btn.active {
    border-color: var(--accent);
    color: var(--text-primary);
  }

  .preset-name { font-weight: 500; }
  .preset-desc { font-size: var(--text-xs); color: var(--text-muted); margin-top: 1px; }

  .add-preset {
    color: var(--text-muted);
    font-size: var(--text-sm);
    border: 1px dashed var(--border);
    justify-content: center;
    padding: var(--space-2);
  }

  .add-preset:hover { color: var(--accent); border-color: var(--accent); }

  .preset-save-row {
    display: flex;
    gap: var(--space-2);
    align-items: center;
  }

  .preset-save-row input {
    flex: 1;
    min-width: 0;
  }

  .btn-accent-sm {
    background: var(--accent);
    color: var(--accent-text);
    padding: 4px 10px;
    border-radius: var(--radius-sm);
    font-size: var(--text-xs);
    font-weight: 600;
    flex-shrink: 0;
  }

  .btn-ghost-sm {
    background: var(--bg-elevated);
    color: var(--text-secondary);
    border: 1px solid var(--border);
    padding: 4px 10px;
    border-radius: var(--radius-sm);
    font-size: var(--text-xs);
    flex-shrink: 0;
  }

  .btn-ghost-sm:hover { color: var(--text-primary); }

  /* Run button */
  .run-wrap {
    padding: var(--space-4);
    margin-top: auto;
    border-top: 1px solid var(--border-subtle);
  }

  .run-btn {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    background: var(--accent);
    color: var(--accent-text);
    font-weight: 700;
    font-size: var(--text-md);
    border-radius: var(--radius-md);
    letter-spacing: 0.01em;
  }

  .run-btn:not(:disabled):hover {
    background: var(--accent-hover);
  }

  .run-icon { width: 14px; height: 14px; }

  @keyframes spin { to { transform: rotate(360deg); } }
  .spinner {
    display: inline-block;
    width: 14px; height: 14px;
    border: 2px solid rgba(0,0,0,0.2);
    border-top-color: var(--accent-text);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }
</style>
