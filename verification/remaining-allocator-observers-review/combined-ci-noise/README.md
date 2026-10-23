# Combined CI noise addon

After the base independent review was sealed, root requested the exact proposed
five-test CI noise commands against the same immutable reviewed source snapshot.
Both Debug and Release pass all five test processes with
`MIXER_ALLOCATOR_NOISE=1` and features
`experimental-span-execution,experimental-capability-native`:
`span_function_cache_allocations`, `span_execution_allocations`,
`experimental_allocations`, `experimental_capability_guest_allocations`, and
`capability_ffi_allocations`. Guest occupancy stays `(16, 8388608, 8388608)`.

`run.py` records the exact commands, 240-second command bounds, tools,
environment, complete logs, unchanged source tree, and source/archive/base-seal
bindings. `receipt.json` and this addon's seal supplement the earlier sealed
review; they do not mutate or replace it. The source is still baseline `020f909`
plus only the four reviewed test overlays. The workflow file belongs to root and
was not edited by this lane.

These are local Mac host runs. Hosted CI results remain pending integration;
physical devices were not discovered or used, and release/GA qualification stays
separate.
