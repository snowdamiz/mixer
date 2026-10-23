# Independent Android appearance descriptor review

The reviewed private Java data reader has no actionable finding in this scoped
review. Root still owns acceptance; no GA gate is verified by this directory.
The exact product source and test hashes are in
[candidate-1/receipt.json](candidate-1/receipt.json), together with all command
arguments, output hashes, tool versions and 28 before/after input checks. The
source snapshot contains both Java files, the exact four pure Swift foundation
sources, the frozen appearance contract and this independent harness.

Observed command: `python3 -B verification/android-appearance-descriptor-review/verify.py`.
The script preserves attempts and refuses to overwrite candidate-1; a later rerun
must choose a new output directory. Transient executables/classes and the unpacked
TSV are ignored; the exact corpus bytes are preserved in gzip archives.

All 7,990 independent cases passed Java's default VM, Java `-Xint`, and Swift
Debug/Release, with 182 accepted and 7,808 rejected inputs. JDK 25.0.4.1 compiled
Java 17 class files using `--release 17 -Xlint:all -Werror`. This is host Java
execution, not execution under Android ART or an Android build qualification.
The independent Java harness made 89,438 assertions per VM run. The product Java
test harness separately passed this corpus with 16,494 assertions.

The fresh concrete corpus uses no production/design validator as its expected
acceptance oracle. It covers every field of the shared/system-font,
shared/bundled-font and explicit-platform branches with missing/extra fields,
wrong types, string/number violations; all truncations of the default bytes;
noncanonical alternate spellings; forbidden raw byte values; depth/value/array/
string construction excess; 160 deterministic coherent random themes; all eight
unique weight/style font pairs; 64 resource entries; 16 fonts plus 48 icons;
maximum strings; exact 16 MiB aggregate bytes; and a valid canonical descriptor
of exactly 65,536 bytes versus an invalid 65,537-byte descriptor. All accepted
cases were compared against each runtime's full retained data: the independent
Java encoder reconstructs the complete root from the exposed immutable values,
and Swift emits production canonical bytes. Both must reproduce every input byte.
This checks accepted data, rather than only matching schema decisions.

For every accepted Java value, recursive map/list probes attempt mutation through
ordinary methods, entry.setValue, key/value views, iterators and sublists.
Complete retained canonical bytes also remain equal after overwriting the caller's
source byte array. The probe additionally checks package privacy, final retained
fields and observed rejection at depth/array/string construction guards. Source
inspection confirms the global value/depth guard runs before child allocation or
collection insertion, and every raw retained collection is wrapped immutably.

Source audit: canonical sorted unique ASCII keys and shortest unsigned integers
are admitted directly, printable strings permit only quote/backslash escapes,
and exactly one final LF is required. Closed fields and fixed enums cover every
schema object/alternative. Resources enforce exact IDs, case-folded paths,
positive per-file/aggregate sizes, digest/provenance constraints and all font
scale/locale/direction restrictions even when unreferenced. Bundled faces require
font resources, unique weight/style pairs and requested normal weights. All text
line boxes and toggle envelope/row relationships match the reviewed Swift code.
Java rejects UInt64 values above Long.MAX_VALUE before schema validation; no
accepted field exceeds 4 MiB, so this changes rejection staging, not the accepted
byte set. Java's fixed IllegalArgumentException labels are not a promise to match
Swift's error classification.

This evidence covers only descriptor data admission and ownership. It establishes
no font/SFNT/PNG validity, resource capture, platform bootstrap, Android runtime,
renderer/widget consumption, installed/signed authority, physical iOS/Android
appearance, accessibility/performance matrix, immutable published FieldLog
consumption, signing, store, customer or release qualification. No physical device
was accessed and no production source was edited by the reviewer.
