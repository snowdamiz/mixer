# Selected native open constructor correspondence candidate

This packet connects the selected File/OpenOptions constructors to the exact
installed Rust 1.99.0 `aarch64-apple-darwin` implementation at
`b940084d7eb6a299eb4bfeb8e34901bc051e7ac4`. It is evidence for the inherited
logical public interface and requested backing. Independent review and root
selection remain pending. Actual immutable caller and executable composition,
P0 data, pricing authority, runtime, healthy cleanup, FieldLog, OTA and GA remain
pending.

`summary.json` states the result and boundary. `symbolic-correspondence.json`
records the source/LLVM/native argument and guard relationships. The source146
tree stays `690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185`.
`input-bindings.json` rehashes the four inherited sealed packets and three exact
root acceptance/amendment files. No product source, status, plans or gates were
edited. No Git changes were made by this lane.

The original frozen LLVM has no generic open constructor bodies. The one
root-authorized LLVM query copied all 146 original files and appended only two
inert used pointers and a minimal output-open wrapper to one copied module.
Exact append bytes, original references, compiled manifest, command, environment,
tool hash and predeclaration are retained. `compiler-plan.json` was announced to
root as SHA256
`9c949b21460a3f5343c4b3d23f84f60b57f7fc111dcf159ea58dee329db0310d`
before launch. The query succeeded in 5.15 seconds, emitted LLVM only, waited for
its owned child and removed its owned workspace after full inventory. It did
not link or run an executable. Its opt-level-0 wrappers remain distinct from
the installed optimized standard library bodies.

The generic LLVM evaluator executes only active alloca/store/load/GEP, tuples,
calls and connected branches. It proves that File::open<&Path> constructs the
12-byte read-only options, and the output wrapper constructs write/create_new
options with read/append/truncate/create disabled. Both preserve the Path
pointer/length through AsRef and reach the exact installed OpenOptions::_open
symbol. These forced instantiations do not prove that an actual immutable setup
caller or loader executable has been linked to those bodies.

Two root-authorized, bounded disassembly calls retained four additional exact
symbols: OpenOptions::_open, borrowed CString specialization,
CString::_from_vec_unchecked and CStr::from_bytes_with_nul. Three existing
frozen native bodies supply open_c, its closure and allocating File path helper.
All 438 instruction words and 46 relocations are rechecked directly against
the installed archive/object bytes. Assembly annotations never authorize the
behavior. Expected missing-symbol warnings on metadata and nonmatching archive
members are retained and checked; all selected bodies exist exactly once.

The offline dataflow model evaluates these words over synthetic registers and
bytes. It fails closed on unsupported instructions and call edges. Allocator,
memcpy/memchr, libc, OS-function and unwinder calls are explicit interface stubs;
their private implementations are outside this packet and the inherited unit.
No native instructions or product operations execute. In particular, the
memchr interface stub does not prove its private compiled implementation.

The results include 131 complete synthetic path routes; 768 combinations of
options, custom flags and mode; 3,800 raw CStr cases covering eight alignments
and every first-NUL position through length384; eight finite retry traces;
three capacity/OOM/landingpad cases; and 23 rejected adverse controls. The
controls alter active LLVM operands and branches while retaining comments,
native instructions while retaining assembly, raw bytes, relocations, the
threshold, termination, allocation size, reserve/shrink guards, deallocation
length, CLOEXEC and OS-error tag shift. They also reject unsupported active
instructions and source digest tampering.

The selected constructor interface establishes:

- For `n<384`, a fixed384-byte source scratch operand and no CString backing
  request. The installed frame496 is a separate compiler footprint, not the
  inherited scratch price.
- For `n>=384`, requested size `n+1`, alignment1, before NUL validation. Valid
  CString uses the same backing: capacity `n+1` bypasses reserve at old length
  `n`, then the incremented length equals capacity and bypasses shrink.
- Both valid callback return and NulError clean up the original backing once.
  CString drop clears its first byte before deallocation. An explicitly
  synthetic landingpad test verifies its cleanup instructions; it does not
  qualify real unwinder selection or healthy cleanup.
- Selected option defaults exclude both dynamic Error::new branches in the
  installed open_c CFG. Returned NUL errors use the exact static record and
  relocated message; returned OS errors use the borrowed errno and tag2/shift32.
- The accepted logical price stays `768+7*n`; Error native price stays23.
  This is not CPU, syscall count, time, RSS, physical stack or an actual root
  pricing grant. Private EINTR retries have no finite bound. Capacity/OOM
  handlers do not return io::Error or establish healthy refusal.

Replay only the pure-host checks:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B verification/swift-guarded-snapshot-native-open-binary-closure/review.py --check
PYTHONDONTWRITEBYTECODE=1 python3 -B verification/swift-guarded-snapshot-native-open-binary-closure/freeze.py --check
```

Do not replay `collect.py` or `query.py`: they preserve one-shot coordinated
commands and are guarded against a second command receipt. Native simulator,
emulator, device, UI/capture and global process inventories stayed paused.
Compiler/disassembler children were waited and their owned groups are absent.
The initial Python import incident and exact authorized cleanup are recorded
in `cleanup-import-incident.json`. Failure history is preserved with exact
helper snapshots and stdout/stderr under `commands/`.
