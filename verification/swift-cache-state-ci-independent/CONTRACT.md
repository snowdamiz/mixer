# Independent closed cache-state CI review

This lane owns only this directory. Before root seals a candidate, review reads
only accepted frozen implementation source and approved old CI runner patterns.
It neither reads the active producer directory nor runs its mutable output.

The exact cache-state implementation is
`f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b`.
The producer and independent implementation seals are separately pinned in the
contract builder. Only three selected library files and the 25 selected API
source files may enter the initial independent compiler check.

The predeclared API roster is 25 dispositions per Debug and optimized mode:
two successful compiles and executions, and 23 intended compile refusals. Each
refusal requires exit 1, no timeout, no executable, the intended error code and
message, every intended primary span in the exact probe, and no unrelated error
at any nested diagnostic level. The source-derived contract has 38 primary
target spans per mode, including all 16 private envelope constructor fields.

Any fresh Rust execution is serial, uses at most 60 seconds per child and a
600-second global active deadline; cleanup/retention has at most 60 additional
seconds. The inherited launcher is resolved through its own --print sysroot
spelling and the actual compiler is hashed and queried. No installation,
fallback compiler, arbitrary pack/hash override or product-cap change is allowed.
All Rust injection/test variables and inherited temporary paths are removed;
TMPDIR/TMP/TEMP point to owned scratch. No runtime/target/native discovery,
computer use, capture, simulator/emulator, phone or other-project process work.

After root provides a frozen candidate, independent checks will use an owned
copy, review its fixed inventory and runtime custody, exercise normal execution,
and run deliberate negative controls in isolated mutations. A normal run must
prove every named method is listed once and executed exactly once within its
declared groups, including zero ignored/failed/measured methods and the exact
declared filtered count for each subgroup. Cases, complete layouts, API targets,
source bytes, snapshots, runner/tool identity and cleanup need explicit receipts.
Historical failures remain historical; fresh output does not infer performance
equivalence, public general admission, canonical runtime, other compiler/target,
native, FieldLog, signing/store, operational or GA qualification.

The filesystem claim is limited to a trusted, quiescent checkout. Hashing and
path checks do not establish adversarial race resistance.
