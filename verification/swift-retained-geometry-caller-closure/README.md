# Caller / Closure alternate diagnostic geometry candidates

This packet prepares source-bound candidate facts for exactly Caller and Closure
from the root-accepted alternate capture identity packet, seal SHA256
`5ec27f9a01bc046341bd0833044d10c0803ce546f9607dc2595e423c0a5fe569`.
It imports and runs no verifier, compiler, model, test, native program, version
query, process probe, UI or screen capture. All preparation uses Python standard
library file/text inspection and hashing, with a 50-second alarm and 55-second
command bound. Raw distinct IR/assembly bytes total 111,430,754, below 128 MiB;
derived files are bounded to 8 MiB. Whole raw artifacts are hashed without copying.

The unchanged source manifest has 146 members and tree SHA256
`91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f`.
Both exact raw hashes, complete function spans and source spans are rechecked.
The excerpts retain complete Caller and Closure functions, including the sole
normal return in each, with original byte/line anchors and hashes. Debug records
bind Caller to source 853–862 and the exact closure expression at 861:36.

Preparation command, from `/Users/andreyyurlov/Documents/dev/mixer`:

```
python3 -B verification/swift-retained-geometry-caller-closure/prepare_facts.py
```

## Fixed local reservations and slots

Let `E_C` and `E_L` be Caller and Closure entry SP respectively. Caller pushes
32 bytes, subtracts three pages of 4,096 and a final 1,680, yielding
`S_C = E_C - 14000`. Its common epilogue adds 12,288, then 1,680 and the saved-state
32, restoring entry SP. All three normal CFG paths reach this one epilogue.
Its four `ldr xzr,[sp]` probes touch the explicitly reserved stack; this packet
does not qualify fault, guard-page or OS handling.

The complete assembly and matching IR stores/calls map the following contiguous
intervals. Offsets use `S_C`, not an arbitrary normalized physical address.

| Caller offset | Bytes | Mapped storage |
| ---: | ---: | --- |
| 0 | 64 | Eight native pointer spills: child destination, reservation temporary, outer sret, account, fixture, attempt, expected, quote temporary |
| 64 | 24 | `%_6`, quote branch result |
| 88 | 24 | `%_7`, selected quote result |
| 112 | 24 | `%_14`, reservation branch result |
| 136 | 24 | `%_15`, reservation result |
| 160 | 13640 | `%_23`, complete child destination C |
| 13800 | 48 | `%_25`, closure capture record |
| 13848 | 24 | Three pointer debug spills |
| 13872 | 96 | Six 16-byte quote/reservation/residual debug spills |
| 13968 | 32 | Saved x28/x27 and x29/x30 |

The native reservation follows the SP instructions. The separately mapped IR
slots account for 13,904 bytes inside it; they are neither the native frame bound
nor a transitive peak. No additional outgoing stack argument allocation or dynamic
SP adjustment is present in these two whole native functions. Outgoing callees
still have unknown additional frames and resource effects.

Closure subtracts 48 and restores 48 on its sole normal return. Its local attempt
copy occupies `[E_L-48,E_L-16)` and x29/x30 occupy `[E_L-16,E_L)`. It loads fixture
from capture offset 0, copies 32 attempt bytes from offset 8, and loads expected
from offset 40. This maps the native argument copy, without bounding any borrowed
provenance, root, account, path, Cell or claim pointee.

## Destinations, lifetimes and coordinate limits

On Caller’s generated success route, Dispatch receives hidden sret x8 equal to
`S_C+160 = E_C-13840`, matching `%_23` and its 13,640-byte allocation. The child
interval ends at `E_C-200`; the closure record begins there. After Dispatch
returns, Caller performs an explicit 13,640-byte copy from C to incoming outer
sret `%_0`. The native destination is reloaded from the saved incoming x8 pointer.
The outer result’s concrete base, rebase, physical relations and upstream lifetime
remain unknown here. A pointer spill supplies no outer allocation or backing bound.
The refusal paths pass `%_0` directly to two external FromResidual call sites.

Closure forwards its exact incoming `%_0` sret to Body with no GEP, cast or PHI.
Closure's prologue and argument setup leave x8 unchanged before the Body call;
preservation across Body execution is not claimed. It allocates no result buffer.
Body’s complete carrier production and Dispatcher’s capture-copy/return mapping
belong to the separate lane; the sret signature alone does not prove initialized
allocated carrier coverage or a backing bound.

The direct call sites provide candidate coordinate deltas:
`DispatchEntrySP = E_C-14000` and `BodyEntrySP = E_L-48`. They require independent
whole-frontier semantic review before use as reviewed same-base relations.
No cross-callee peak or numeric union is calculated. Native reservation persists
through each activation; source moves, debug lifetimes and StorageDead do not
release it early. C survives Dispatch’s return through the outer copy on success;
the Closure attempt slot survives the Body call through normal return.

The source still returns `WholeQuotePending` from selected_whole_quote_v1. Emitted
success-route code does not establish an admitted runtime path. No local
invoke/landingpad/resume, personality/LSDA or cleanup edge appears in the complete
Caller/Closure functions. CFI describes saved-state unwinding; external callee,
destructor, fault and unwind-runtime continuations remain unbounded.

## Alignment and verifier limits

The candidate native arenas retain `physical_alignment=null`. Every numerical
rebase and SP delta is explicit, but no reviewed physical entry-base congruence
is supplied. LLVM `align 8` operands are recorded as validity requirements.
All SP deltas preserve an already proved modulo16 congruence; they cannot create
one. Neither a q-register access nor CFI proves a stronger base fact. The outer
result’s actual base congruence is also unresolved.

The v2 verifier README, source and synthetic example construction were inspected
as text. Its closed CURRENT_BINDING still pins the **original** capture argv and
plan. The alternate build adds only `-C link-dead-code=yes`, with different pinned
argv/plan and explicit alternate flags. It cannot be truthfully supplied to that
verifier unchanged. `verifier-review-fragments.json` is explicitly not a complete
certificate or executable input: it preserves alternate provenance, unreviewed
rebases, null congruences and missing facts. No verifier was imported or executed.

`unresolved-obligations.json` records every native call site: eight in Caller and
one in Closure, including the two refusal sites and external `_memcpy`. It retains
all thirteen conditional source backing obligations, acquisition/P0/C0–C5
partitions, pointer escapes and later destroy/drop/token continuations. Original
files, optional executable, proof/error graphs, shared Cancellation, claims and
allocator/OS backing capacities and final destruction are pending. Source pointer
or descriptor widths do not discharge those obligations.

Independent semantic review and root approval are pending. Every result remains
alternate configuration, local diagnostic evidence only. Original capture missing
targets, admission, physical devices, paused native checks, complete capacity,
prices, root funding/custody, FieldLog, OTA and GA remain unchanged or pending.
Product source, global metadata and all frozen input packets are unchanged.
No runtime or native instance was started, so this preparation owes no cleanup.
