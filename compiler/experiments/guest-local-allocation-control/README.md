# Verify guest-local allocation recovery

This arm64 macOS replay uses the pinned Swift 6.3.3 WASI archive and
the exact reviewed VM archive. Nine aligned 4,096-byte allocations fill
the fixed-page fixture. The tenth returns WASI `ENOMEM`. The test frees
one middle block, allocates at the same address, checks survivor and
replacement canaries, and frees the remaining blocks. A fresh generation
repeats the test. The fixture checks one page and zero host calls on
every turn.

Run the inert controls from the Mixer checkout.

```sh
python3 -B compiler/experiments/guest-local-allocation-control/test_controls.py
```

For the complete replay, use the recorded SDK, Rust toolchain, and
locked local Cargo inputs. Run from a checkout containing the pinned
source commit. The replay needs new scratch and receipt paths outside
that checkout.

```sh
area=$(mktemp -d)
git worktree add --detach "$area/source" abadfffa100c61b724e4f021d294b0e1377fb00b &&
python3 -B compiler/experiments/guest-local-allocation-control/run.py \
  --checkout "$area/source" --scratch "$area/work" --output "$area/receipt.json" &&
git worktree remove "$area/source"
```

The runner removes scratch after publishing the receipt and confirming
command closure. Preserve any scratch it reports as unresolved.
[Reviewed replay receipt](../../../verification/receipts/l03-guest-allocator-release-strict-abadfffa10.json)
