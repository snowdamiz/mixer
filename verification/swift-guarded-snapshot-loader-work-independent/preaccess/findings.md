Independent preaccess source audit

The inspected loader overlay and ten unchanged validator/callee files match their member hashes in accepted descriptor source tree `450b6d9b3a05d160e19fa888b68173286b8f6af20ecc7216fdf86283f09b308a`. No active producer files were read. The accompanying script verifies these member hashes and exercises only finite abstract countermodels. It does not execute the loader or validator and does not prove a source-action coefficient.

The positive successful-credit cut is plausible for the inspected validator loops. No source counterexample was found in this preaccess pass. `Meter::work` checks cancellation/deadline, performs checked addition, rejects widening of work used beyond the original budget, and only then updates usage. Every observed debit failure propagates to a terminal error rather than retrying.

Source obligations for the later bridge review:

* Reader `take(n)` admits n=0 and is not sufficient evidence of positive progress. Reader byte debits1. Both LEB loops call byte before their backedges. The source-copy loop uses nonempty chunks and debits chunk.len before copying.
* Buffer reserve copies old elements after work1 on each iteration; Buffer push calls work1 before growth. T is Copy, so element destruction has no product callback. T can be an aggregate, so element-copy bytes and source actions must remain explicit.
* Metadata section iteration reads a positive-credit section ID and count. Every counted section-entry loop either reads a byte/uint or performs Buffer push. UTF8 loops debit1 before processing each lead or continuation byte.
* Heap-build outer iteration has no direct credit but calls sift, whose first action is work1 on every path, including an empty child range. Adjacent duplicate-name checks call compare_names, whose trailing work1 covers either empty name. These are important tests against falsely treating an empty comparison as zero-credit progress.
* Body iteration starts with r.count, which reaches uint/byte1 even when parameter and local vectors are empty. The initial control push also debits1. Every opcode loop starts with byte1. Function-call parameter pop iterations reach pop_any/work1. Local replication reaches Buffer push/work1. Branch-table and numeric-pop loops have positive debit callees.
* Exact ABI's resolver uses a fixed34-element `find` loop. Its callback may execute34 times and each comparison has a byte-length envelope. The enclosing import debit does not make those source actions free. Fixed2 segment-family iteration can run with no segments and therefore no inner debit; its fixed work must survive in a no-credit segment.
* Source cleanup/error paths, derived functions, coercions, temporary values, return/argument places, tuple/array repeats, aggregate copies, and closed callbacks remain operation-envelope obligations. Counting token occurrences or treating a Std call as proof of zero source work does not close them.

Loader obligations independent of original validator credits:

* Each read request can call read32 times, including Interrupted; each retained file has an EOF request even when its byte length is0. The retained chunk loop adds requests by ceil(length/4096).
* Environment pointer iteration is0..=64, hence65 observations when rejecting a missing terminator. Argv has at most64 strings; each C-string scanner examines at most4096 bytes.
* Environment insertion sort has at most2016 key comparisons for64 entries. Key byte comparisons need their own bounded byte work, and serialized output, string scans, reserve/resize, fixed arrays, and aggregate moves need their actual lengths/types.
* Parse hex has32 iterations and two digit-callback calls per iteration. Compile identity `any` has5 entries. Header reserved-byte scans, list position/contains/ordering checks, source equality, identity encodings, and hashes need explicit bounded source surfaces or excluded-private-Std boundaries.

Targeted released-producer review tests:

1. Reject or separately retain a synthetic zero-credit repeat and an unclassified cycle.
2. Preserve fixed34 resolver callbacks and fixed2 empty-inner segment iteration; avoid counting either occurrence only once.
3. Validate successful-credit partition including B=0, one trailing failed debit, nested loop return paths, empty names, and zero-length take.
4. Reject unknown call targets, unbounded closed callbacks, omitted derived/copy/coercion surfaces, or unsupported MIR statements/terminators rather than assigning them zero.
5. Check the source/MIR member binding and compiler/mode; compare the independently derived operation envelope and native requested-byte dimensions with the quote without executing product paths.

Native and physical checks are pending under the user pause. No process inventory or capture was performed. No production, GA, loader-execution, compiler, VM, guest, cache, scope, constructor, or writer evidence is claimed.
