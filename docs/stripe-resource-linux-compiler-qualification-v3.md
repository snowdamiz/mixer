# C6 V3: bounded base-export and cleanup corrections prepared

V3 is a separate source/evidence packet. It preserves the closed V2 failure and
changes only the two root-selected contracts, their observation fields and
necessary V3 selection/attempt paths. No V3 container or compiler attempt has
occurred. Root must separately select this source before native execution.

The first correction applies only to base-library `docker cp -L` tar decoding.
It accepts the requested SONAME leaf or that exact leaf followed by a dot and
one or more nonempty dot-separated ASCII decimal version components. Thus
`libgmp.so.10` and `libgmp.so.10.5.0` both match requested `libgmp.so.10`.
Wrong prefixes, paths, empty components, signs, letters and non-ASCII digits
fail. This does not use broad prefix matching or filename normalization.

The new base-only wrapper delegates to the unchanged exact decoder after
validating the observed leaf. It still requires exactly one regular file and
rejects PAX, sparse metadata, links, special members, extra members and nonzero
tail bytes. The existing byte/envelope limits remain fixed. No host filesystem
extraction occurs. After decoding, the unchanged ELF parser, exact
`ELF SONAME == requested SONAME`, inherited byte hashes, dependency providers
and GNU-version checks still apply. The runner retains each requested path,
requested SONAME, raw export binding, observed member name, body length and
SHA256 before later checks can fail. Rejected exports retain their request,
raw bytes and decoder error rather than invented decoded facts.

Products and notices continue to call the unchanged exact-name decoder.
The header decoder is byte-identical. Their naming contracts receive no
versioned-basename exception. The actual retained V2 GMP tar is a host fixture:
one regular `libgmp.so.10.5.0` member, 526,632 bytes, body SHA256
`39b6701812ed7135f28df49352b3f6664c7a9f56880a3fe50c1b87cd7681db9b`,
ELF SONAME `libgmp.so.10`. V3 accepts it only through the new base wrapper;
the old exact-name decoder still rejects it for requested `libgmp.so.10`.

The second correction adds exactly the observed cleanup response
`error: no such object: ` followed by the exact owned container name. It still
requires exit code 1 and stdout `[]`. Existing uppercase variants remain
accepted. No case folding, substring acceptance or new daemon-error rule is
introduced. The random-name/token/image/child/ID ownership fence, removal
ordering, cleanup reserve and all-outcome handling remain unchanged. The actual
V2 lowercase response passes the new host control; foreign names, suffixes,
other casing, other message types, extra lines, wrong statuses and wrong stdout
shapes fail. Prior V2 cleanup evidence and its failed predicate are preserved.

All thirty-four V2 controls remain, with nine additional controls covering the
selected changes. Forty-three host controls, shell syntax, the sealed C5/C4/C3
data audit and the adapter's default refusal pass. `source-diff.patch` retains
the exact source changes; `source-diff.json` identifies unchanged functions,
files and test bodies. Original preparation, failed attempts, image-inspection
proposal, V2 source and V2 failure seals remain unchanged.

The parent image remains
`hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde`,
with required Linux arm64 child
`sha256:c2d3bab1f8a854f5ca3bb220e5463f4fe39036caa2ce22dfd7614a30404279de`.
The exact 177,326,080-byte C5 tar, 36-package lock, reviewed helper/NIF source,
matching original ERTS headers, compiler/sysroot invocation and all process,
isolation, storage, output and deadline bounds remain unchanged.

The new root-selection path is
`verification/stripe-webhook-resource-ingress-root-review/linux-compiler-qualification-v3-selection.json`.
The prospective attempt owns only V3's exclusive `attempt-1` directory.
After a separately reviewed root selection, the exact command is:

```sh
python3 -B verification/stripe-resource-linux-compiler-qualification-v3/run_qualification.py --execute --selection-sha <SHA256-of-new-root-selection>
```

Compiler qualification, complete base/header closure, `/usr/bin/cc` integration,
actual helper/NIF/BEAM behavior and all thirty resource rows remain pending.
No frozen catalog/authority work, publication, physical-device run or GA
acceptance is performed. Root owns shared trackers and Git operations.
