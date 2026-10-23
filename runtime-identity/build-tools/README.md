# Capture declared build inputs

`capture.py` replaces every digest in a validated runtime descriptor with a digest
computed from copied file bytes. It produces a private, deterministic snapshot
containing `descriptor.json`, `inputs.json` and content-addressed `objects/`.
The tool requires Python 3.11+ on macOS or Linux and a trusted, already-built
`mixer-identity` executable. No manifest value is executed as a command.

This captures a **declared** input set. It does not discover the complete native
link graph, verify compiler/SDK version labels, attest a build, sign an artifact,
or prove the eventual linker consumed these objects. Build adapters must collect
the entire resolved graph and use these captured bytes for the actual build.
The current native build generators do not do that yet.

Every descriptor field ending in `_sha256`, including dependency and capability
entries, needs exactly one binding. Binding pointers identify existing digest
fields; they cannot change execution policy or introduce new descriptor fields.
For example, one entry in a complete binding file is:

```json
{
  "pointer": "/engine/artifact_sha256",
  "kind": "file",
  "files": [{"name": "libmixer_vm.a", "path": "native/libmixer_vm.a"}]
}
```

The complete file has the closed shape `{"schema":1,"bindings":[...]}`.
`file` binds exactly one raw file. `collection` binds zero or more files, sorted
uniquely by logical `name`. Its digest is SHA-256 of an explicit generated manifest
object, including names, byte counts and each raw file hash. The representation is
ASCII JSON with sorted object keys, no insignificant spaces, and one final LF:
`{"files":[{"bytes":N,"name":"...","sha256":"..."}],"schema":1}\n`.
Even an empty collection has a real manifest object. Source filesystem paths do
not enter the descriptor or output inventory; moving an identical input set does
not change the snapshot. Names and relative paths use printable ASCII components,
with no `.`/`..`, empty components or backslashes.

```sh
swift build --package-path runtime-identity --product mixer-identity
python3 runtime-identity/build-tools/capture.py capture \
  --descriptor descriptor.json --bindings bindings.json \
  --input-root /absolute/private/build-inputs \
  --output /absolute/private/new-snapshot \
  --identity-tool /absolute/path/to/mixer-identity
python3 runtime-identity/build-tools/capture.py verify \
  --snapshot /absolute/private/new-snapshot \
  --expected-fingerprint EXPECTED_64_HEX_FINGERPRINT \
  --identity-tool /absolute/path/to/mixer-identity
```

Use a trusted private output parent. Output creation is exclusive; existing files
and directories remain untouched. Captured objects are mode0400 in a mode0700
directory. The completion manifest is written last after file and directory sync;
a partial directory cannot verify. Source reads pin each directory component below
the trusted input root with `openat` and reject symlinks, nonregular files, FIFOs,
oversize files and observed changes during the read. Hashing and copying use the
same bytes from the same opened descriptor, in 64KiB chunks. Input reads have no
hard wall-clock guarantee on slow or remote filesystems.

Bounds are 1MiB for binding/capture manifests, 128KiB for the runtime descriptor,
4,096 file entries, 1GiB per file and 4GiB of distinct declared source-path bytes.
Generated collection metadata is additionally bounded by the final 1MiB manifest.
Repeated references to one source path reuse its captured object. These are local
tool bounds, independent of mobile VM payload/linear-memory limits.

Verification requires an expected runtime fingerprint from the trusted build
configuration. It hashes every declared captured object, checks exact binding
coverage and collection contents, and recomputes the runtime fingerprint through
the public Swift validator from a private copy of the descriptor. It never relies
on the original input files. Read-only permissions prevent accidental writes;
they do not defend against a privileged or same-user writer changing permissions.
A build consuming a snapshot must retain ownership and check the bytes it uses.
The snapshot is not a whole-filesystem point-in-time snapshot or signed provenance.

```sh
python3 -B -m unittest discover -s runtime-identity/build-tools/tests -v
```

The tests use the actual Swift CLI. They cover copied-byte identity, relocation,
source mutation, exact limits, ambiguous manifests, missing/duplicate bindings,
path escape and symlink/FIFO rejection, partial capture, object corruption and
collection tampering. They do not qualify a complete application build graph.
