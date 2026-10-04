<script>
  import {
    batchSets, batchSingles, batchSources, framesPerSet, scanning,
    addToBatch, rescanBatch, updateSet,
  } from '../stores/batch.js'
  import { isRunning } from '../stores/process.js'

  let showSingles = $state(false)

  const included = $derived($batchSets.filter(s => s.include).length)

  async function chooseFolder() {
    const dir = await window.pywebview?.api?.open_folder_dialog()
    if (dir) await addToBatch([dir])
  }

  function setAll(include) {
    batchSets.update(list => list.map(s => ({ ...s, include })))
  }

  function fmtEv(ev) {
    if (ev === null || ev === undefined) return '?'
    const r = Math.round(ev * 10) / 10
    return (r > 0 ? '+' : r < 0 ? '−' : '±') + Math.abs(r).toFixed(1)
  }

  function name(path) {
    return path.split('/').pop()
  }

  function reveal(path) {
    window.pywebview?.api?.reveal_in_finder(path)
  }
</script>

<div class="batch">
  <div class="toolbar">
    <button class="btn" onclick={chooseFolder} disabled={$isRunning}>Add folder…</button>
    <label class="fps">
      Frames per set
      <select bind:value={$framesPerSet} onchange={rescanBatch} disabled={$isRunning || !$batchSources.length}>
        <option value={0}>Auto</option>
        {#each [2, 3, 4, 5, 6, 7, 9] as n}<option value={n}>{n}</option>{/each}
      </select>
    </label>
    <span class="summary">
      {#if $scanning}
        Scanning…
      {:else if $batchSets.length}
        {$batchSets.length} set{$batchSets.length !== 1 ? 's' : ''} · {included} selected
        {#if $batchSingles.length}
          · <button class="link" onclick={() => (showSingles = !showSingles)}>
              {$batchSingles.length} single frame{$batchSingles.length !== 1 ? 's' : ''} skipped
            </button>
        {/if}
      {/if}
    </span>
    {#if $batchSets.length && !$isRunning}
      <button class="link" onclick={() => setAll(included < $batchSets.length)}>
        {included < $batchSets.length ? 'Select all' : 'Select none'}
      </button>
    {/if}
  </div>

  {#if showSingles && $batchSingles.length}
    <div class="singles">
      Not part of any bracket: {$batchSingles.map(name).join(', ')}
    </div>
  {/if}

  {#if !$batchSets.length}
    <div class="empty">
      {#if $scanning}
        <p>Scanning for brackets…</p>
      {:else}
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" class="empty-icon">
          <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/>
        </svg>
        <p class="empty-title">
          {$batchSources.length ? 'No bracketed sets found' : 'Drop a folder of bracketed exposures'}
        </p>
        <p class="empty-sub">
          {#if $batchSources.length}
            Try a fixed number of frames per set.
          {:else}
            Sets are detected from capture time and exposure.
            <button class="link" onclick={chooseFolder}>Choose folder…</button>
          {/if}
        </p>
      {/if}
    </div>
  {:else}
    <ul class="sets">
      {#each $batchSets as set (set.id)}
        <li class="set" class:excluded={!set.include} class:running={set.status === 'running'}>
          <input
            type="checkbox"
            checked={set.include}
            disabled={$isRunning}
            onchange={e => updateSet(set.id, () => ({ include: e.currentTarget.checked }))}
            aria-label="Include {name(set.paths[0])}"
          />
          <div class="frames">
            {#each set.paths as p, j}
              <div class="frame">
                {#if set.thumbs[j]}
                  <img src={set.thumbs[j]} alt={name(p)} />
                {:else}
                  <div class="ph"></div>
                {/if}
                <span class="ev">{fmtEv(set.evs[j])}</span>
              </div>
            {/each}
          </div>
          <div class="info">
            <span class="first">{name(set.paths[0])}</span>
            <span class="meta">{set.paths.length} frames · {set.paths[0].split('/').slice(-2, -1)[0]}</span>
          </div>
          <div class="status">
            {#if set.status === 'running'}
              <div class="mini-track"><div class="mini-fill" style="width: {set.pct}%"></div></div>
              <span class="msg">{set.message}</span>
            {:else if set.status === 'queued'}
              <span class="msg muted">Queued</span>
            {:else if set.status === 'done'}
              {#if set.resultThumb}<img class="result" src={set.resultThumb} alt="Result" />{/if}
              <button class="link" onclick={() => reveal(set.outputPath)}>Show</button>
            {:else if set.status === 'error'}
              <span class="msg err" title={set.message}>Failed: {set.message}</span>
            {/if}
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .batch {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    margin: calc(-1 * var(--space-4));  /* use the full preview area, edge to edge */
  }

  .toolbar {
    display: flex;
    align-items: center;
    gap: var(--space-4);
    padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--border-subtle);
    font-size: var(--text-xs);
    color: var(--text-secondary);
  }

  .btn {
    background: var(--bg-elevated);
    color: var(--text-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 4px 12px;
    font-size: var(--text-xs);
  }
  .btn:hover:not(:disabled) { color: var(--text-primary); border-color: var(--text-muted); }

  .fps { display: flex; align-items: center; gap: var(--space-2); }
  .fps select { font-size: var(--text-xs); padding: 2px 6px; }

  .summary { flex: 1; color: var(--text-muted); }

  .link {
    background: none;
    border: none;
    padding: 0;
    color: var(--accent);
    font-size: inherit;
    cursor: pointer;
  }
  .link:hover { color: var(--accent-hover); }

  .singles {
    padding: var(--space-2) var(--space-4);
    font-size: var(--text-xs);
    color: var(--text-muted);
    border-bottom: 1px solid var(--border-subtle);
  }

  .empty {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    color: var(--text-muted);
    text-align: center;
  }
  .empty-icon { width: 40px; height: 40px; opacity: 0.6; }
  .empty-title { color: var(--text-secondary); font-size: var(--text-md); margin: 0; }
  .empty-sub { font-size: var(--text-sm); margin: 0; }

  .sets {
    list-style: none;
    margin: 0;
    padding: var(--space-2) var(--space-3);
    overflow-y: auto;
    flex: 1;
  }

  .set {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-md);
    border: 1px solid transparent;
  }
  .set:hover { background: var(--bg-surface); }
  .set.running { border-color: var(--accent-dim); background: var(--bg-surface); }
  .set.excluded .frames, .set.excluded .info { opacity: 0.35; }

  .frames { display: flex; gap: 4px; flex-shrink: 0; }

  .frame {
    position: relative;
    width: 72px;
    height: 48px;
    border-radius: var(--radius-sm);
    overflow: hidden;
    background: var(--bg-overlay);
  }
  .frame img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .ph { width: 100%; height: 100%; }

  .ev {
    position: absolute;
    left: 3px;
    bottom: 2px;
    font-family: var(--font-mono);
    font-size: 9px;
    color: #fff;
    background: rgba(0, 0, 0, 0.6);
    padding: 0 3px;
    border-radius: 2px;
  }

  .info { display: flex; flex-direction: column; min-width: 0; flex: 1; }
  .first {
    font-size: var(--text-sm);
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .meta { font-size: var(--text-xs); color: var(--text-muted); }

  .status {
    width: 220px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: var(--space-2);
    font-size: var(--text-xs);
  }

  .mini-track {
    width: 80px;
    height: 4px;
    border-radius: 2px;
    background: var(--bg-overlay);
    overflow: hidden;
    flex-shrink: 0;
  }
  .mini-fill { height: 100%; background: var(--accent); transition: width var(--transition); }

  .msg {
    color: var(--text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .msg.muted { color: var(--text-muted); }
  .msg.err { color: var(--error); }

  .result {
    width: 54px;
    height: 36px;
    object-fit: cover;
    border-radius: var(--radius-sm);
    border: 1px solid var(--success);
  }
</style>
