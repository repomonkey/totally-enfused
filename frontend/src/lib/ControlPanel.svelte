<script>
  import { onMount } from 'svelte'
  import { bridgeReady } from '../bridge.js'
  import { settings, saveSettings, applyPreset, outputPathFor, presetFromSettings } from '../stores/settings.js'
  import { images, referencePath } from '../stores/images.js'
  import { mode, batchSets, batchRun, updateSet } from '../stores/batch.js'
  import {
    processState, processProgress, processStage, processMessage,
    processError, resultPath, resultPreview, resetProcess, isRunning
  } from '../stores/process.js'

  let { tools, onResult } = $props()

  let presets = $state({})
  let openSection = $state('align')
  let customPresetName = $state('')
  let showPresetSave = $state(false)

  onMount(async () => {
    await bridgeReady()
    presets = (await window.pywebview.api.get_presets()) ?? {}
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
    return outputPathFor($images[0]?.path, $settings)
  }

  function pipelineParams() {
    return {
      align_enabled: $settings.align_enabled,
      align_mode: $settings.align_mode,
      align_grid_points: $settings.align_grid_points,
      align_crop: $settings.align_crop,
      exposure_weight: $settings.fusion_exposure_weight,
      saturation_weight: $settings.fusion_saturation_weight,
      contrast_weight: $settings.fusion_contrast_weight,
      hard_mask: $settings.fusion_hard_mask,
      levels: $settings.fusion_levels,
      jpeg_quality: $settings.output_quality,
      exposure_optimum: $settings.fusion_exposure_optimum,
      highlight_protect: $settings.fusion_highlight_protect,
      motion_enabled: $settings.motion_enabled,
      motion_sensitivity: $settings.motion_sensitivity,
      split_enabled: $settings.split_enabled,
      split_line: $settings.split_line,
      split_feather: $settings.split_feather,
      split_tilt: $settings.split_tilt,
      sky_exposure_optimum: $settings.sky_exposure_optimum,
      sky_highlight_protect: $settings.sky_highlight_protect,
      sky_saturation_weight: $settings.sky_saturation_weight,
    }
  }

  async function runProcess() {
    if ($isRunning) return
    if ($mode === 'batch') return runBatch()
    const paths = $images.map(i => i.path)
    if (paths.length < 2) return

    const outputPath = buildOutputPath()
    if (!outputPath) return

    resetProcess()
    processState.set('running')
    await saveSettings($settings)
    const ref = paths.indexOf($referencePath)
    await window.pywebview?.api?.process({
      input_paths: paths,
      output_path: outputPath,
      ...pipelineParams(),
      reference_index: ref >= 0 ? ref : null,   // null: the backend picks the frame nearest 0 EV
    })
  }

  async function runBatch() {
    const sets = $batchSets.filter(s => s.include)
    if (!sets.length) return
    resetProcess()
    processState.set('running')
    processMessage.set(`Starting ${sets.length} sets…`)
    batchRun.set(sets.map(s => s.id))
    for (const s of $batchSets) {
      updateSet(s.id, () => s.include
        ? { status: 'queued', pct: 0, message: '', outputPath: null, resultThumb: null }
        : { status: 'ready' })
    }
    await saveSettings($settings)
    await window.pywebview?.api?.process_batch({
      sets: sets.map(s => ({ paths: s.paths, output_path: outputPathFor(s.paths[0], $settings) })),
      ...pipelineParams(),
    })
  }

  function cancel() {
    processMessage.set('Cancelling…')
    window.pywebview?.api?.cancel()
  }

  async function saveCurrentPreset() {
    if (!customPresetName.trim()) return
    const key = customPresetName.toLowerCase().replace(/\s+/g, '_')
    const preset = {
      name: customPresetName,
      description: 'Custom preset',
      ...presetFromSettings($settings),
    }
    await window.pywebview?.api?.save_preset(key, preset)
    presets = { ...presets, [key]: { ...preset, builtin: false } }
    showPresetSave = false
    customPresetName = ''
  }

  const batchCount = $derived($batchSets.filter(s => s.include).length)
  const canRun = $derived(!$isRunning && ($mode === 'batch' ? batchCount > 0 : $images.length >= 2))
  const runLabel = $derived($mode === 'batch'
    ? (batchCount ? `Blend ${batchCount} set${batchCount !== 1 ? 's' : ''}` : 'No sets selected')
    : ($images.length < 2 ? 'Load 2+ images' : 'Blend Images'))
  const outputPreview = $derived($mode === 'batch'
    ? outputPathFor($batchSets.find(s => s.include)?.paths[0], $settings)
    : buildOutputPath())
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

  <!-- Motion -->
  <div class="section-wrap">
    <button class="section-header" onclick={() => toggleSection('motion')}>
      <div class="header-left">
        <span>Motion</span>
        {#if $settings.motion_enabled}
          <span class="badge on">On</span>
        {/if}
      </div>
      <svg class="chevron" class:open={openSection === 'motion'} viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
        <path d="M1 1l4 4 4-4"/>
      </svg>
    </button>
    {#if openSection === 'motion'}
    <div class="section-body">
      <label class="toggle-row">
        <input type="checkbox" bind:checked={$settings.motion_enabled} />
        <span>Take moving areas from one frame</span>
      </label>
      <span class="hint-text">
        For waves, clouds, leaves or people that moved between frames. Without it,
        they're averaged into a blur. Moving areas come from the frame marked REF in
        the strip: the one nearest 0 EV, unless you pick another.
      </span>
      {#if $settings.motion_enabled}
        <div class="field">
          <label for="motion-sens">Sensitivity <span class="val">{formatSliderValue('motion_sensitivity')}</span></label>
          <input id="motion-sens" type="range" min="0" max="1" step="0.05" bind:value={$settings.motion_sensitivity} />
          <span class="hint-text">Higher catches subtler movement.</span>
        </div>
      {/if}
    </div>
    {/if}
  </div>

  <!-- Sky / foreground split -->
  <div class="section-wrap">
    <button class="section-header" onclick={() => toggleSection('split')}>
      <div class="header-left">
        <span>Sky</span>
        {#if $settings.split_enabled}
          <span class="badge on">On</span>
        {/if}
      </div>
      <svg class="chevron" class:open={openSection === 'split'} viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
        <path d="M1 1l4 4 4-4"/>
      </svg>
    </button>
    {#if openSection === 'split'}
    <div class="section-body">
      <label class="toggle-row">
        <input type="checkbox" bind:checked={$settings.split_enabled} />
        <span>Blend the sky separately</span>
      </label>
      <span class="hint-text">
        Blends twice, with a line between sky and foreground, like a graduated filter.
        Fusion settings apply below the line; these apply above it.
        {#if $mode === 'single'}Drag the line in the preview to place it.{/if}
      </span>
      {#if $settings.split_enabled}
        <div class="field">
          <label for="split-line">Line position <span class="val">{Math.round($settings.split_line * 100)}%</span></label>
          <input id="split-line" type="range" min="0.05" max="0.95" step="0.01" bind:value={$settings.split_line} />
        </div>
        <div class="field">
          <label for="split-feather">Feather <span class="val">{Math.round($settings.split_feather * 100)}%</span></label>
          <input id="split-feather" type="range" min="0" max="0.5" step="0.01" bind:value={$settings.split_feather} />
          <span class="hint-text">How gradual the change is. Use more where trees or rocks cross the horizon.</span>
        </div>
        <div class="field">
          <label for="split-tilt">Tilt <span class="val">{$settings.split_tilt}°</span></label>
          <input id="split-tilt" type="range" min="-20" max="20" step="0.5" bind:value={$settings.split_tilt} />
        </div>
        <div class="field">
          <label for="sky-optimum">Sky brightness target <span class="val">{formatSliderValue('sky_exposure_optimum')}</span></label>
          <input id="sky-optimum" type="range" min="0.3" max="0.7" step="0.01" bind:value={$settings.sky_exposure_optimum} />
          <span class="hint-text">Lower favours the darker frames, for deeper sunset colour.</span>
        </div>
        <div class="field">
          <label for="sky-highlights">Sky highlight protection <span class="val">{$settings.sky_highlight_protect}%</span></label>
          <input id="sky-highlights" type="range" min="0" max="20" step="1" bind:value={$settings.sky_highlight_protect} />
        </div>
        <div class="field">
          <label for="sky-saturation">Sky saturation weight <span class="val">{formatSliderValue('sky_saturation_weight')}</span></label>
          <input id="sky-saturation" type="range" min="0" max="1" step="0.05" bind:value={$settings.sky_saturation_weight} />
        </div>
      {/if}
    </div>
    {/if}
  </div>

  <!-- Fusion -->
  <div class="section-wrap">
    <button class="section-header" onclick={() => toggleSection('fusion')}>
      <div class="header-left">
        <span>Fusion</span>
        {#if $settings.split_enabled}
          <span class="badge">Foreground</span>
        {/if}
      </div>
      <svg class="chevron" class:open={openSection === 'fusion'} viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
        <path d="M1 1l4 4 4-4"/>
      </svg>
    </button>
    {#if openSection === 'fusion'}
    <div class="section-body">
      <div class="field">
        <label for="fw-exposure">Exposure weight <span class="val">{formatSliderValue('fusion_exposure_weight')}</span></label>
        <input id="fw-exposure" type="range" min="0" max="1" step="0.05" bind:value={$settings.fusion_exposure_weight} />
        <span class="hint-text">Favours well-exposed pixels. This is what lifts shadows and holds highlights, so keep it near 1.</span>
      </div>

      <div class="field">
        <label for="fw-optimum">Brightness target <span class="val">{formatSliderValue('fusion_exposure_optimum')}</span></label>
        <input id="fw-optimum" type="range" min="0.3" max="0.7" step="0.01" bind:value={$settings.fusion_exposure_optimum} />
        <span class="hint-text">The brightness exposure weighting aims for. Higher lifts shadows; lower keeps skies deeper.</span>
      </div>

      <div class="field">
        <label for="fw-highlights">Highlight protection <span class="val">{$settings.fusion_highlight_protect}%</span></label>
        <input id="fw-highlights" type="range" min="0" max="20" step="1" bind:value={$settings.fusion_highlight_protect} />
        <span class="hint-text">Ignores near-white pixels in the exposure weighting, so a bright frame's washed-out sky can't dilute a darker frame's colour.</span>
      </div>

      <div class="field">
        <label for="fw-saturation">Saturation weight <span class="val">{formatSliderValue('fusion_saturation_weight')}</span></label>
        <input id="fw-saturation" type="range" min="0" max="1" step="0.05" bind:value={$settings.fusion_saturation_weight} />
        <span class="hint-text">Prefers more colourful pixels when choosing between frames. It doesn't add saturation; do that in your editor.</span>
      </div>

      <div class="field">
        <label for="fw-contrast">Contrast weight <span class="val">{formatSliderValue('fusion_contrast_weight')}</span></label>
        <input id="fw-contrast" type="range" min="0" max="1" step="0.05" bind:value={$settings.fusion_contrast_weight} />
        <span class="hint-text">Prefers sharp, detailed pixels. Mainly for focus stacks; high values can add noise.</span>
      </div>

      <div class="field">
        <label for="fw-levels">Blend levels <span class="val">{$settings.fusion_levels}</span></label>
        <input id="fw-levels" type="range" min="1" max="29" step="1" bind:value={$settings.fusion_levels} />
        <span class="hint-text">How far blending spreads. Lower values can show halos; leave at the maximum unless you see a problem.</span>
      </div>

      <label class="toggle-row">
        <input type="checkbox" bind:checked={$settings.fusion_hard_mask} />
        <span>Hard mask</span>
      </label>
      <span class="hint-text">Takes each pixel from a single frame instead of averaging. For focus stacks; adds noise to exposure blends.</span>
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
        {runLabel}
      {/if}
    </button>
    {#if $isRunning}
      <button class="cancel-btn" onclick={cancel}>Cancel</button>
    {/if}
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

  .badge.on {
    background: var(--accent-dim);
    color: var(--accent);
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
    position: sticky;
    bottom: 0;
    background: var(--bg-surface);
    border-top: 1px solid var(--border-subtle);
  }

  .cancel-btn {
    width: 100%;
    margin-top: var(--space-2);
    padding: var(--space-2);
    background: none;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    color: var(--text-secondary);
    font-size: var(--text-sm);
  }
  .cancel-btn:hover { color: var(--text-primary); border-color: var(--text-muted); }

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
