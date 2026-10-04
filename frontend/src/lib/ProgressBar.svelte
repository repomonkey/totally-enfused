<script>
  import {
    processState, processProgress, processMessage,
    processError, resultPath, isRunning, isDone, doneMessage
  } from '../stores/process.js'

  async function revealInFinder() {
    await window.pywebview?.api?.reveal_in_finder($resultPath)
  }
</script>

{#if $processState !== 'idle'}
<div class="progress-bar-wrap">
  {#if $processState === 'error'}
    <div class="bar-row error">
      <svg class="icon" viewBox="0 0 16 16" fill="currentColor">
        <path d="M8 1a7 7 0 100 14A7 7 0 008 1zm0 4v4m0 2v1" stroke="currentColor" stroke-width="1.4" fill="none" stroke-linecap="round"/>
      </svg>
      <span class="message">{$processError}</span>
    </div>
  {:else if $isDone}
    <div class="bar-row done">
      <svg class="icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 8l3.5 3.5L13 5"/>
      </svg>
      <span class="message">{$doneMessage || `Done — ${$resultPath.split('/').pop()}`}</span>
      {#if $resultPath}
        <button class="reveal-btn" onclick={revealInFinder}>Show in Finder</button>
      {/if}
    </div>
  {:else if $processState === 'cancelled'}
    <div class="bar-row">
      <span class="message">Cancelled{$doneMessage ? ` — ${$doneMessage}` : ''}</span>
    </div>
  {:else}
    <div class="bar-row">
      <span class="message">{$processMessage || 'Processing...'}</span>
      <span class="pct">{Math.round($processProgress)}%</span>
    </div>
    <div class="track">
      <div class="fill" style="width: {$processProgress}%"></div>
    </div>
  {/if}
</div>
{/if}

<style>
  .progress-bar-wrap {
    padding: var(--space-2) var(--space-4);
    background: var(--bg-surface);
    border-top: 1px solid var(--border-subtle);
  }

  .bar-row {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-bottom: 4px;
  }

  .bar-row.done { color: var(--success); }
  .bar-row.error { color: var(--error); }

  .icon { width: 14px; height: 14px; flex-shrink: 0; }

  .message {
    flex: 1;
    font-size: var(--text-sm);
    color: var(--text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .done .message, .error .message {
    color: inherit;
  }

  .pct {
    font-size: var(--text-sm);
    font-family: var(--font-mono);
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .track {
    height: 3px;
    background: var(--border);
    border-radius: 2px;
    overflow: hidden;
  }

  .fill {
    height: 100%;
    background: var(--accent);
    border-radius: 2px;
    transition: width 200ms ease;
  }

  .reveal-btn {
    background: var(--bg-elevated);
    color: var(--text-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 2px 10px;
    font-size: var(--text-xs);
    flex-shrink: 0;
  }

  .reveal-btn:hover {
    color: var(--text-primary);
    border-color: var(--text-muted);
  }
</style>
