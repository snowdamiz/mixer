# C6 V2: explicit arm64 inspection correction prepared

This separate packet preserves the original prepared logic and failed C6
attempt. Its only runtime command change adds `--platform=linux/arm64` to
`docker image inspect`. Root-selection and packet/attempt paths move to the new
V2 ownership. One additional host guard checks the actual runner call site's
complete image-inspection argv. The existing thirty-three controls remain.
No native V2 attempt is selected or executed by this preparation.

The first attempt failed before container creation because unqualified inspection
returned the parent OCI index in `Id` and `Descriptor`. Root's separately bounded
explicit-platform inspection returned exit zero in 0.04612870793789625 seconds.
Its 1,927-byte stdout has SHA256
`2a07514cc042c9fc5e768124689fda0a0817882021d9dc09dc675ee773d8e7b3`,
exactly matching the retained C5 output. The unchanged strict image validator
passes that output. This establishes the index-versus-child metadata projection
difference; it is not compiler, base-runtime-file or resource qualification.

The parent remains
`hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde`.
The required Linux arm64 child remains
`sha256:c2d3bab1f8a854f5ca3bb220e5463f4fe39036caa2ce22dfd7614a30404279de`.
The C5 compiler tar remains 177,326,080 bytes with SHA256
`30583d60dc1206350578b75b34aa93af77de321c6efb606fe51c5c5371e1347b`.
The 36-package lock remains SHA256
`4db8b41afffdf796acaec18bcc3b5574be593af0c11c4cb860b39da5d64a36b4`.
No digest, platform predicate, compiler/sysroot invocation, header input,
dependency validator, isolation setting, deadline, storage/output bound or
cleanup rule is relaxed.

`source-diff.json` and `source-diff.patch` retain the complete source comparison.
`prepare.py`, `qualification.py`, `native-qualify.sh` and `collect_host.py` are
byte-identical copies. `run_qualification.py` changes only the root-selection
path and image-inspection argv. `test_preparation.py` adds only the argv guard.
The V2 packet's `HERE` automatically gives its own immutable `attempt-1` path;
the failed original attempt is never reused or overwritten.

The root-selection path is
`verification/stripe-webhook-resource-ingress-root-review/linux-compiler-qualification-v2-selection.json`.
The exact execution command after a new root selection is:

```sh
python3 -B verification/stripe-resource-linux-compiler-qualification-v2/run_qualification.py --execute --selection-sha <SHA256-of-new-root-selection>
```

The proposed C6 work remains one stopped-container base ELF/header preflight,
then one bounded private compiler-prefix qualification only if the unchanged
preflight succeeds. It retains four compilations of the original reviewed
helper/NIF sources into noexec output storage, repeat-byte comparison, ELF
evidence, and identity-fenced cleanup. It never executes a helper, loads a NIF,
starts BEAM or runs any of the thirty resource rows. `/usr/bin/cc` integration,
full ABI/runtime qualification, notice/redistribution acceptance, service/rootfs
construction and all product/GA gates remain pending.

The original preparation's 27 bindings, failed attempt's 40 bindings and
inspection proposal's six bindings remain unchanged. The frozen catalog and
authority lane is untouched. V2 host evidence, exact source hashes, the root's
explicit-platform evidence bindings, proposal, template and seal are retained
only under this new ownership. Root owns tracking and Git operations.
