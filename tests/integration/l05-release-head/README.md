# Replay the signed release head in the console

Run this from the repository root on a host with Python 3.12 or later, Node,
npm, Elixir with Hex, and PostgreSQL tools on `PATH`. The runner builds the
console from public `71e6ffa51e857d5a1eda3f74c26941996ed275de` and runs the
existing signed-release ExUnit test with browser checkpoints in a disposable
copy. PostgreSQL and the HTTP bridge listen on loopback. The bridge serves the
production bundle and forwards only session and release-head reads.

```sh
mkdir -p verification/local
python3 -B tests/integration/l05-release-head/mixer_l05_replay.py \
  --receipt verification/local/l05-browser-replay.json
```

1. Open an owned incognito Acid preview tab. Use the scratch directory printed
   by the runner to find `ready.json`.
2. For each new `phase` in `ready.json`, navigate the tab to its `url`. The
   empty and denied phases use single-use URLs. Each sets an ordinary session
   cookie that Phoenix issued through the synthetic OIDC fixture.
3. In `preview_evaluate`, wrap the contents of `mixer_l05_dom.js` in parentheses
   and call the function with `expectedStatus`. Set `awaitPromise` to true.
   Save the returned value as JSON at `observationFile`. Write to a sibling
   file first and rename it into place so the runner reads a complete document.
4. Repeat for anonymous, empty, first publish, second publish, rollback, and
   denied. Close the owned preview tab. Check the final receipt for six phase
   results, a passing ExUnit result, fixture database removal, and port reuse.

The release writes run through the existing fixture's browser-session publish
and CLI HTTP publish and rollback paths. The console reads each committed
head. The denied phase uses the second fixture tenant against the same target
after rollback. The runner checks both the rendered fields and the response
that Phoenix sent to the browser.
