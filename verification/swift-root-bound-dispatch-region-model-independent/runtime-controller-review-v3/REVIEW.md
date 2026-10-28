# V3 controller source review: release one exact root-owned attempt

C01–C03 are corrected in controller
`53b6386bf796716c259e4a9f4ff709c908dee8e3d2c4d5f5e34f93f54ee7af69`
(12,668 bytes). No new blocking source finding remains. Recommend root release
this exact controller with Python `-B`, assertions enabled, and unchanged host
plan `5a2950e97e714e3628546d9b73aa2918c72f23f1221c64806823f978dc2c32e8`:
one compile, then only on compile success one 24-test invocation, no retry, under
one cumulative 55-second budget. No compiler, controller or model code was
imported or executed during this review; no passing test outcome is claimed.

The exact old controller remains unchanged. The supplied diff independently
reconstructs the entire successor. The model's 11-member preparation seal,
source/plan/roster/toolchain/linker/SDK and controller/diff custody checks covered
118 unique inputs before and after with identical bytes/hashes.

- **C01:** the iterative inventory uses no-follow type checks, counts both
  directories and files, and enforces the 64-member/32-MiB aggregate limits before
  hashing any generated file. The regular binary must occur in this bounded
  inventory before its launch. The inventory repeats after test closure and its
  file rows must equal the pre-run inventory; binary hashes must also match.
  Final bounded inventory precedes owned removal. Oversize, unsupported type,
  missing binary or inventory drift prevents pass. Returned hash rows describe
  regular files; equal rows do not assert that empty directories were identical.
- **C02:** all input, binary, generated and observation hashes finish before
  signal blocking. The one-way cutoff now precedes the pending-signal snapshot.
  Pre-cutoff handled or pending signals cannot be lost by the former ordering
  gap. Post-cutoff signals sampled before the pending snapshot may conservatively
  cause refusal. Only receipt publication follows; no compiler, hash, parse,
  inventory or input verification occurs after cutoff. The receipt explicitly
  scopes later signals outside the completed observation.
- **C03:** bounded strict-JSON control reads hash the same bytes before parsing.
  Plan/seal/manifest/roster/toolchain/SDK controls have their expected hashes, and
  duplicate object keys or nonfinite constants refuse. The whole 11-member
  preparation, seal and controller enter pre/post pins. The cached verified
  roster supplies 24 distinct expected names. The fixed pinned member roster has
  unique safe paths and the present pin rows have no inconsistent collisions;
  this finite review does not qualify an arbitrary future manifest schema.

Serial compile/test flow, output caps, absolute deadlines from one START,
WNOWAIT leader retention, exact session/group custody, signaling before reaping
and final group absence remain intact. Cleanup and posthash exceptions enter
ERRORS, which gates pass. Generated removal follows proven owned closure. The
final pin recheck must finish before the completed observation/cutoff. Runtime
availability and actual success remain to be observed in root's single attempt.

No model source correction is requested. Original producer and independent
packets are preserved. No canonical product/metadata change, commit, push,
native/UI/capture/device action or process inventory occurred. All actual
physical capacity, prices, grants, funding, complete ownership and GA remain
pending regardless of any later model-only host result. No child/build artifact
was created here and no cleanup is owed.
