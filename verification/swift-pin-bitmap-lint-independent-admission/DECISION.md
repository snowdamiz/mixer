# Independent source review and unselected host proposal

Accept the frozen correction **for one bounded host verification attempt**.
No source semantic blocker was found. This is not Rust compilation, lint or
runtime acceptance, and it does not authorize canonical installation or a
workflow dispatch. The assigned independent escalation role is fresh-context
`gpt-6-astra`, `xhigh`, under product-plan sections 20.3 and 24.4; the coordinator
retains final selection and integration authority.

The parent-supplied revision is `6d57e05e58e6d614e58a0a4dc0fad661264fb46f`.
No Git command was used to reverify it. The actual 136-member canonical VM
closure was rehashed as
`af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b`.
All 31 producer-seal members and 15 overlays match seal
`89505e8f873e5c225d711f8ae923bd8149db30a74603c49dddb523639cb11052`;
the complete proposed VM closure is
`7f188bd7b0fe12244936bcbde3f1e4b2f9d9d3fedd43cacbf750d4ba55684748`.
The source-only review independently replayed all 199 edits and reproduced the
exact formatted-to-candidate diff. The actual earlier Clippy evidence remains
50 baseline errors, 46 candidate errors, 45 shared and 51 in the union. It is
neither an exhaustive lint inventory nor evidence of bitmap causation.

## Findings

| Area | Decision and source evidence |
| --- | --- |
| Full Result ownership | Accept. The three test helpers write complete `Result` values into caller-owned `Option` slots. No boxing, allocation wrapper, error truncation, generic return disguise or lint suppression is added. `ConstructionFailure::Cleanup` retains its complete ownership tail. |
| Completion and cleanup precedence | Accept. Cache construction still completes its phase before returning the operation result; completion failure wins. Preparation failure still drops/refunds the original adopted proof, with cleanup failure taking precedence. Pin preparation, pinning and completion retain their order. |
| Allocation observer interval | Accept. All 15 corrected measured closures execute the same operation and slot write while `measure`/`measure_extended` is active, then extract the slot after the observer resets. Every slot starts as `None`, so replacement cannot drop an older owned value. The 147 ordinary wrappers preserve their existing enclosing observer placement, including unwraps that were already inside measured success paths. No cleanup call moves across the cutoff. |
| Fixture setup allocation order | Accept with a precise scope. Struct-update syntax evaluates the replacement field before the default base, so incidental fixture setup allocation order can differ. `Program::default` is a deterministic value constructor with no registry/authority effects. Those Program constructions and byte encoding occur before the allocation observer is enabled. The actual measured validation/creation intervals and assertions are unchanged. |
| Lifetimes, borrowing and types | Plausible for host compilation, not proven. Returned cache, pin and instance values are owned types with no borrowed lifetime tied to the new slot. The mutable slot borrow ends on the helper call; the owned Result is then moved by `unwrap`. Temporary adopted-pair values remain alive through their constructor call. No escaped reference, extra alias or partial owner destruction was found. Rust 1.99 compilation remains the decisive type/borrow check. |
| Complete callers | Accept. The ledger's 147 ordinary call adaptations and 15 measured closures are accounted for. `construct_owned` appears only in execution_tests and the directly authorized value_operation_tests consumer; all other 136-member Rust paths were checked for this name. The local cache construct/pin helpers retain their original visibility. |
| Omitted completion tests | Accept. Lexical scope replaces four explicit non-Drop drops. Borrowed phases still leave scope without completion; the original ledger charge remains. `ReservationTicket` owns only owner/category/bytes and has no Drop. `FrameCompletion` derives Copy, making `let _ = completed` equivalent for destruction. Retained-charge, retry and cleanup assertions remain. |
| Assertions and outcomes | Accept. All 271 test methods, 2,225 assertion macros and 95 selected diagnostic literals retain their ordered inventories. Three constant predicates become compile-time assertions, so violation fails compilation. SL13/SL14 behavior changes remain the previously accepted candidate. Error-path `expect_err` now prints the Debug success value on an unexpected success; the expected error value and refusal remain intact. |
| Numeric, rows and pointers | Accept. The contiguous opcode set is exactly 0x45 through 0xc4. Integer intervals and 32-byte complete-row observation preserve endpoints/remainders. `growthwork = 76,611,584` makes the specific `>= 1 + growthwork` to `> growthwork` replacement overflow-safe. Address 1 uses exposed provenance, keeping u8 alignment, oversized length and all other pointer/error/storage fixtures. |
| Production authority | Accept scope. The formatted borrowed bitmap file is unchanged; cache.rs changes only its cfg(test) inspection expression after the production prefix. Default policy, lifecycle/execution/frame production files, Cargo manifests and lockfile remain exact. No dependency, public/signed default, cancellation or capability change is introduced. |
| Rust availability | Host-only. The producer's documented API high-water mark is 1.88 for `as_chunks`, with exposed provenance 1.84 and inline const 1.79. No declared `rust-version` was found in the source basis. This proposal keeps Rust 1.99.0 and does not qualify a lower MSRV. |

Eight independent guarded source controls passed with 1,328 data assertions.
They do not import producer implementation modules. Twenty-seven fresh guarded
host controls passed, including actual lean input materialization, exact argv,
tool/link drift, failed source/tool postflights, 699-terminal rejection cases,
strict Clippy failure, mocked timeout/output/custody and whole-driver cleanup.
The command helper is the previously reviewed implementation with only its
fixed child-count/seconds constants adapted. Generic source inventory, formatter
evidence and Clippy parsing functions remain exact except the 15-overlay message.
These are mock custody facts, not live process receipts.

Two control-preparation failures are retained in preparation-history.json:
standard-library SSL class initialization after replacing socket.socket, then
fd-relative pure-fixture teardown refused by the write guard. The corrections
preload standard-library mock definitions before the subject guard and use
absolute local teardown paths. No effect guard was loosened. All failed pure
scratch directories were removed. No compiler or product runtime ran locally.

## Proposed six-child attempt

Only the new candidate is materialized. `command-plan.json` gives the exact
argv templates and expansion roots. The plan contains compiler identity (30 s),
Node identity (30 s), standard rustfmt over exactly the 15 overlay paths (60 s),
all-feature/all-target locked/offline Clippy with unchanged `-D warnings` (300 s),
full all-feature Debug (600 s), and full all-feature Release (600 s). Each test
command adds `--include-ignored --test-threads=1 --show-output`; `--locked` and
`--offline` remain explicit. No filter, exclusion, suppression or fallback is
used. Exactly 699 terminal `ok` lines and summary passes, zero failed/ignored/
measured/filtered tests, and all nine named Node oracles once are required in
each profile. Clippy failure retains its diagnostics and stops before tests.

Proposed bounds are 1,800 active seconds plus 60 cleanup seconds, six sequential
managed children, 8 MiB per captured stream and 32 MiB aggregate. The finite
per-child maxima sum to 1,620 seconds. The inherited helper additionally refuses
a child when its complete timeout plus cleanup margin does not fit. Root still
selects the final allowance; these are verification bounds, never production
resource policy. No baseline repeat or automatic retry is proposed.

The proposal records the exact compiler `-vV`, required full host component
names, and all five regular Rust tool binary hashes. Their identities are checked
before and after every managed command. The existing Rust 1.99.0 minimal
rustfmt/Clippy provisioning command remains in a separate two-minute workflow
step; the driver cannot install or fall back to another compiler.

Each command checks the full 136-member source before it starts and attempts
source and binary postflights independently in finally, preserving the primary
error. Formatting retains all 15 exact before/after files, the unified diff,
full before/after closure identities and the successful complete formatted
manifest. A change outside the overlay set fails closed. The subsequent lint
and both test profiles use exactly that retained formatted tree. Ownership,
direct-child reap and owned-group absence gate scratch removal; unresolved
custody preserves the entire owned scratch. No other process inventory occurs.

## Explicit Node oracle admission

The coordinator selected the existing-host-binary approach: resolve `node` once
without executing it, require a regular executable outside the checkout and
runner temp, freeze its resolved path/SHA256/device/inode/mode, and record its
exact version, V8/components, execPath, platform and architecture in the second
managed child. There is no Node installer, fallback binary or discovery run.
The same real path is supplied through `MIXER_NODE`; a private first-in-PATH
`node` link covers experimental_oracle.rs, which hardcodes `Command::new("node")`.
The other three test files use MIXER_NODE. Both the binary and private link are
checked before and after every managed command. The environment allowlist
removes NODE_OPTIONS, NODE_PATH, preload variables, Rust wrappers and ambient
compiler flags. The exact PATH contains only the private Node directory, the
selected Rust tool directory, `/usr/bin` and `/bin`.

The nine tests are 3 differential, 1 experimental validation, 3 float and 2
table/memory cases. Their ordinary Rust Command launches have no setsid,
setpgid, process_group or pre_exec hook. They pipe stdin/stdout/stderr, consume
and close the taken stdin after writing, and call wait_with_output. The fixed
scripts use finite source-built fixture arrays and no child-process/network
imports. Normal Node children therefore inherit the managed Cargo process
group and are covered by its terminal group check and kill-on-failure policy.
They remain development reference oracles; Node is never a production
interpreter dependency. This qualifies only the observed host oracle binary,
not an installed or externally prequalified Node release.

The inherited limitations remain explicit. Rust installer descendants/output
are outside the six-child helper custody record. The helper records direct-child
reap and owned-group absence, not escaped-session descendants or whole-provider
disposal. Individual Node-grandchild terminal records and explicit pipe EOF/
sink-close flags are not recorded. Node's internal captured pipes have no
separate byte cap; fixed trusted finite scripts and the 600-second Cargo group
limit bound this experiment, while outer captured output keeps the stated caps.
Executable pre/post hashes do not establish immutable loaded shared libraries
or defeat transient privileged replacement on a compromised host. No stronger
custody or hermetic provenance claim is made.

The proposed workflow file remains inside this verification packet. No workflow
was installed, selected or dispatched; root owns that next decision. Raw CI
artifacts remain in their existing ignored local directory. Native/UI/capture,
physical-phone, local custody, Unit A, broad hosted and published-package
FieldLog/GA holds remain unchanged. FieldLog run 40802230894 PGID 2424/PID 2621
was not probed, signalled, retried or assumed disposed. No local Git/gh,
compiler, Node, Rust, Swift, Elixir, native runtime, UI, capture, credential,
publication or other-project process operation occurred.
