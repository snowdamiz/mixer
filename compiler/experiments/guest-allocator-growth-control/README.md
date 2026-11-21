# Verify guest allocation with a two-page ceiling

This arm64 macOS diagnostic uses the pinned Swift 6.3.3 WASI allocator
with the reviewed Guest UI V1 VM archive. It first reproduces the
[fixed-page replay](../guest-local-allocation-control/README.md).
The growth fixture then starts at one 64 KiB page and permits a
second page. Both fixtures have zero imports and make zero host calls.

Run with the recorded SDK, Rust toolchain, and locked local Cargo
inputs. Use a disposable checkout at the exact revision below. The
scratch and receipt paths must be fresh and outside that checkout.

```sh
area=$(mktemp -d)
git worktree add --detach "$area/source" 4f9eb3449cb7671b2e83222a28c85696c1741a59 &&
python3 -B compiler/experiments/guest-allocator-growth-control/test_controls.py \
  --checkout "$area/source" --scratch-parent "$area" &&
python3 -B compiler/experiments/guest-allocator-growth-control/run.py \
  --checkout "$area/source" --scratch "$area/work" --output "$area/receipt.json" &&
git worktree remove "$area/source"
```

Allocation 10 grows memory to two pages. The nine existing blocks keep
their canaries. Allocation attempt 26 returns `ENOMEM` at the cap.
Freeing the middle block allows same-address reuse, and drain frees all
remaining blocks. A fresh session repeats the sequence. The VM refuses
each retired handle.

The runner publishes a new receipt and checks command closure before
removing scratch. Preserve any scratch the runner reports as unresolved.
[Reviewed replay](../../../verification/receipts/l03-guest-allocator-growth-strict-41a05264.json) ·
[Independent replay](../../../verification/receipts/l03-guest-allocator-growth-maintained-root.json)
