# Shared observation accounting correction

`isolated-1/receipt.json` freezes committed `3a1bb5a` plus only the root-owned
control and control-test changes. The original two raw WASI usage shapes did
not cover the actual optional observations or nested Copy bindings. The new
upfront allowance counts six `Option<WasiUsage>` shapes: five nested observed
control parameters plus one retained caller observation. It adds464 bytes on
the measured Apple arm64 host, without a new ticket or stored-layout change.

The admission test rejects the old ceiling and the new ceiling minus one,
accepts the exact new ceiling, observes no allocations and zero final charges.
Debug and Release each pass320 full tests, nine reference checks and73 minimal
Swift library tests. Clippy and formatting pass. Independent review also
destroys an actual dispatched WASI owner before exercising standalone deep
control fault paths, so no component header can conceal missing accounting.

`contract-v3/` records the revised cache contract and exact v2 history. Root
acceptance is `acceptance.json`; independently authored evidence is in
`../swift-observation-accounting-review/`. These are named Rust-object bounds,
not compiler-stack, allocator-overhead or RSS measurements. Actual cache and
executor implementation, their composed temporary maps, full target execution,
physical devices, published consumers and GA qualification remain separate.
