<script>
  let { tools } = $props()
  // tools: { enfuse: string|null, align_image_stack: string|null }

  const allGood = $derived(tools && tools.enfuse && tools.align_image_stack)
  const missing = $derived(tools ? [
    !tools.enfuse && 'enfuse',
    !tools.align_image_stack && 'align_image_stack',
  ].filter(Boolean) : [])
</script>

{#if tools && !allGood}
<div class="tool-status">
  <svg class="icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4">
    <path d="M8 2l6 11H2L8 2z" stroke-linejoin="round"/>
    <path d="M8 7v3m0 2v1" stroke-linecap="round"/>
  </svg>
  <div class="text">
    <strong>{missing.join(', ')} not found.</strong>
    Install via Homebrew: <code>brew install hugin enblend-enfuse</code>
  </div>
</div>
{/if}

<style>
  .tool-status {
    display: flex;
    align-items: flex-start;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    background: rgba(212, 163, 54, 0.1);
    border-bottom: 1px solid rgba(212, 163, 54, 0.2);
    color: var(--warning);
  }

  .icon {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
    margin-top: 1px;
  }

  .text {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    line-height: 1.5;
  }

  strong { color: var(--warning); }

  code {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    background: var(--bg-elevated);
    padding: 1px 6px;
    border-radius: var(--radius-sm);
    color: var(--text-primary);
  }
</style>
