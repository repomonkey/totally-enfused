// pywebview injects window.pywebview.api some time after the page loads.
// Calls made before then silently do nothing, so wait for it first.
let ready = null

export function bridgeReady() {
  if (!ready) {
    ready = new Promise(resolve => {
      if (window.pywebview?.api) return resolve()
      const done = () => { clearInterval(poll); resolve() }
      const poll = setInterval(() => { if (window.pywebview?.api) done() }, 100)
      window.addEventListener('pywebviewready', done, { once: true })
    })
  }
  return ready
}
