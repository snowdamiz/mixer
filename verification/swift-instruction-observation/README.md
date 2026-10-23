# Instruction and fuel observation prerequisites

Root-owned additive private control variants preserve actual paired WASI observations at fuel admission, cancellation/deadline, and instruction-count overflow. Original methods delegate with None; no stored fields, public route, policy, ticket or counter order changes. The future executor remains unimplemented.

The original small complete-validated Swift fixture constructs one actual AccountedWasi owner and dispatches ArgsSizesGet before each boundary. Eleven cases cover both success paths, both cancellation/deadline/fuel-limit/fuel-overflow paths, and instruction overflow after its existing one-fuel charge. Reentry preserves the immutable first failure with no further counters, allocations or refunds. Two overflow cases use test-only corrupted scalar counters, not forged proof authority.

Run `python3 verification/swift-instruction-observation/collect.py --name isolated-1`. Each run freezes committed4585220 plus only two source overlays, retains source/log/tool bindings, and excludes active cache/module-gating and Android work. Independent review remains pending; phones and full target execution are not attempted.
