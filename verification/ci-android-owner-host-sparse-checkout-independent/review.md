Independent review accepts the frozen Android owner checkout change for bounded
offline input coverage. No actionable finding was identified in this scope.

The candidate workflow SHA256 is
`fa8fd8887391ffc00f55bc70b370e725cf99ee330c744387f498bea7a2626a88`.
The exact checkout-only delta SHA256 is
`a475d9cb12c1dd9f230f4075d9afb924596ef86ddd838330326d8a0f827e4f14`.
The producer manifest SHA256 is
`27c7a3c226cc1b38fa835f59ce4d7ef12753f05bbd416a17463814b9b45a889f`;
all eleven producer members were checked before and after the independent pass.

The review compared the candidate bytes with canonical workflow bytes at
`ee9f6dc77f88259e2b143fc81dc1085b34a4a943`, tree
`076842155358f5be57a6f97af73577687a32a6d4`. Removing the added checkout
`with` block recovers the exact base workflow. This preserves all other workflow
bytes, action versions, commands, job and step limits, triggers, and artifact
settings. The checkout fetch-depth input remains absent in this job. The private
runner uses Git only for `rev-parse HEAD`; the environment runner reads the
selection context as data. These invocations do not need history beyond the
default shallow fetch.

Fresh finite Git reads independently inventoried only `native/android` and the
four explicit data paths: 304 canonical regular files, 2,108,263 bytes. Git's
non-cone rule evaluator selected all of them and excluded eight sibling or
unrelated control paths. Each canonical blob's Git object identity, byte count,
SHA256, producer manifest entry, and current local content were checked. This
does not repeat the producer's full-tree inventory or scratch materialization;
both remain frozen producer evidence. Source-byte selection is not a measurement
of GitHub transfer size, checkout time, disk allocation, or total CI performance.

The reviewer read both canonical runner sources. A restricted finite AST
interpreter derived their actual source-list expressions without importing or
executing either runner. Closure A has 87 Java inputs, B has 90, and the default
environment invocation has 34. Their union has 193 Java files; adding both
runners and the four JSON inputs gives 199 required paths. All are retained.
This agrees with the frozen producer closure and includes
`NativeEnvironmentPlatformV2.java` in each invocation.

The source/data read boundary was inspected separately from path selection:

- `run-private-owner-host.py` reads the roster at lines 13-14 and freezes its
  explicit sources, itself, barrier map, and descriptor at lines 16-18. Its
  subsequent evidence reads are outputs it created; cleanup rechecks the same
  frozen sources. JDK tools are supplied by the existing runner environment.
- `run-environment-platform-host.py` selects the default environment branch at
  lines 19-21, freezes sources and the five auxiliary files at lines 26-28,
  and uses only `selection['context_revision']` at line 36. Historical packet
  manifest paths inside the selection JSON are not opened recursively.
- `NativeOwnerV2HostTests.java:406` reads the supplied descriptor. Its
  `Fixture` at line 24 seeds the host AssetManager map with those bytes.
- `NativeOwnerV2ConcreteHostTests.java:655` reads the descriptor and supplied
  barrier map. `loadBarriers` at lines 607-616 consumes JSON record and boundary
  values; it does not open record source paths. Reports at lines 651 and 660 are
  outputs. Its fixture seeds the host AssetManager map at line 133.
- `InstalledAppearanceV2.java:34` opens the descriptor through that host
  AssetManager. Both selected AssetManager leaves implement this as a
  `ByteArrayInputStream` from the in-memory map. Packaged APK assets add no
  checkout input to these host invocations.
- The finite Java input set was inspected for filesystem, network, process,
  resource-stream, environment, and loader sites. The relevant read/write
  excerpts are retained in `source-review.json`; the environment Java host
  closures add no filesystem input. Source inspection supplies checkout
  coverage evidence, without executing or qualifying the Java behavior.

Reproduce with:

`python3 -B verification/ci-android-owner-host-sparse-checkout-independent/review.py`

The receipt records Python 3.14.8, Git 2.56.0, source/tree identities, exact
command, scope, and cleanup. Every Git subprocess has a 55-second timeout with
lazy fetching disabled. `commands.json` records argv, input/output identities,
exit status, and stderr. `stdout.txt` retains the pass output. The reviewer
created no scratch checkout, worktree, index, or configuration; no compiler,
JVM, product/CI test, native/UI/capture, stopped Android candidate5 replay,
network operation, or global process inventory was run. No protected hosted,
browser-auth, store, or callback file was edited.

GitHub actions/checkout v4 integration with the new sparse inputs and the existing
JVM job result remain pending root delivery. The earlier CI pass at the base used
the old checkout and does not validate this candidate workflow. No native runtime,
physical-phone, immutable separate-repository FieldLog, OTA, signing, store,
operational, or GA acceptance is supplied. Root owns metadata, commit, push, and
subsequent CI inspection. This independent packet is released read-only when its
manifest is frozen.
