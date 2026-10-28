# Identity network binary export correction

The collector's shared file exporter now explicitly checks
`:ok = :io.setopts(:standard_io, encoding: :latin1)` before checked
`IO.binwrite(File.read!(path))`. This is a source correction and pure-control
packet. It does not claim a corrected Elixir runtime pass or authorize a run.

Only the exact public bootstrap paths `/workspace/downloads/hex.ez` and
`/workspace/tooling/rebar3` gain retained raw command captures. Their fixed host
files are `bootstrap-exports/hex-actual.bin` and `rebar-actual.bin`, each bounded
to 16 MiB and covered by the existing 256 MiB total artifact cap. The command
writes these files before host validation. A finally block records actual
length, SHA256/SHA512, exact owned CID/path, command number, completion flags
and exit result. The raw output and receipt survive length/hash refusal and
owned scratch cleanup. Partial/failed command output remains partial/failed,
and duplicate capture cannot overwrite prior failure evidence. Existing
verified bootstrap filenames are written only after exact downloaded length
and unchanged pinned SHA512 match.

Other allowed exports retain their previous scratch handling. The container
path allowlist and original cap-admission decisions are unchanged. This does
not retain arbitrary file contents or add a secret/private export path.
The same fixed Latin-1 literal supplies all five static call sites, covering
seven expected exports in a complete attempt:

| Export | Bound | Retention before validation |
| --- | --- | --- |
| Hex downloaded archive | 16 MiB | fixed public capture and hash receipt |
| Installed pinned Rebar executable | 16 MiB | fixed public capture and hash receipt |
| Prepared source/dependency/tool tar | 512 MiB | original scratch handling |
| Event stream | 2 MiB | original scratch handling |
| Two fixed semantic JSON receipts | 8 MiB each | original scratch handling |
| Runtime identity JSON | 8 MiB | original scratch handling |

The next dependent Rebar export reads the exact
`/workspace/tooling/rebar3` installed and executed by v2 bootstrap, uses the
same byte transport and retains its public capture before checking its
recorded downloaded size and pinned SHA512. No escript, compiler or package
fallback is introduced. UTF-8 JSON file contents are also transmitted as their
stored bytes through this shared transport; their later JSON decoding is
unchanged.

The reviewed failure is run `40746908101`, delivery
`fb7c7f20f8a308424ef4b7092d19d3d4de2c7627`, artifact `12842685657`.
Actual preparation mounts, all seven tools/CA150, complete bootstrap,
exclusive cross-mount Rebar copy and direct Rebar version passed. All 37 command
streams completed without timeout. The first new failure followed command 28:
Hex export returned exit zero but 1,693,010 bytes with SHA256
`9ec3f63426780b4b34d6486a64785e6e499fec9167ac7c81eaad6de7f0c195f6`, while the exact
pinned downloaded archive has 1,133,941 bytes. Its raw failed export was
unlinked from `.scratch/copy.bin` before host hash refusal, and is absent from
the retained artifact. It has not been reconstructed and presented as observed
bytes in this packet.

A fresh inert pinned Hex download in the independent review, transformed from
Latin-1 to UTF-8, matches that exact recorded export size and SHA256. The
[exact Elixir 1.20.4 IO source](https://github.com/elixir-lang/elixir/blob/v1.20.4/lib/elixir/lib/io.ex#L288-L310)
explains binary writes through the default Unicode standard IO. Together these
support the transcoding cause; they do not constitute corrected runtime proof.
The review also records current OTP 29.1.2 documentation separately from the
actual OTP 29.1.1 runtime. No global/kernel encoding setting is changed.

The FINAL independent runtime review at
`verification/github-delivery-runtime-followup/network-review/` is bound in
`runtime-review-reference.json`: 256 files, tree SHA256
`69832104e969c2746dc99edda71c86961b84c05c1576da1368b19a72fa2e3bb1`, exact packet-manifest
SHA256 `4ccc5ebe10600086473c96afd9aabf68ed63c46068419f5e599ac747f0d1800c`, and decision
SHA256 `28c7248f1eea177d0d4901de594e4f355bb2c888d67da399027ad29a32fe8d57`.
All 256 files were independently rehashed before final binding. Selected raw
proof, including command 28, actual bootstrap/mount/prerequisite observations,
transcoding evidence and exact IO source, is copied without modification under
`proof/runtime-review/`. The inert pinned Hex bytes remain in their original
sealed review and are referenced by exact hash. The owned preparation CID was
removed and its exact absence verified. Product methods ran zero times.

`implementation/canonical.diff`, before/after snapshots and source bindings
cover only collector, controls and the corresponding contract document.
Canonical three-file tree SHA256 is
`0cf7245c95092ec8efb714116660a38bab7b2f22ec8d95384d0be1abe6194bad`.
The command `python3 -B hosted/scripts/test_identity_network_collector.py`
passed all 111 controls in 0.612 seconds on Python 3.14.8, within the unchanged
50-second alarm and global subprocess/socket denial. All 103 prior test method
bodies remain byte-for-byte unchanged. Eight focused additions cover checked
encoding-before-output source, real host byte transport through an inert
runner, high bytes/NUL/all 256 byte values, exact size/hash decisions, retained
public output after host rejection, bounded incomplete/nonzero captures,
no private retention, and no overwrite or cap expansion. They execute no
Elixir VM. Their source assertion and byte model are explicitly pure controls,
not runtime authority.

`implementation/verify-source.py` confirms all 177 committed product blobs
still have digest `023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e`.
Thirty-one original collector constants and literal helpers remain identical,
including all image/bootstrap SHA pins, source roots, resources, capabilities,
mount partitions, helper bytes and limits. Original contract 46 files,
source review 71 files, v1 packet 110 files, v2 packet 64 files and the new
runtime review 256 files rehash exactly. V2's immutable 16-file metadata and
prior review packets were not edited. Workflow and THIRD_PARTY.yml stay
unchanged. Protected live hosted workflow and browser-auth store hashes remain
`fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57` and
`8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299`.

No local Elixir/escript/compiler, Docker/PG, native/UI/capture, hosted replay,
PID/process/custody harness, network fetch, credential/publication, commit/push,
workflow dispatch, plan/status/gate edit or broad cleanup occurred. Pure-test
temporary directories were owned and automatically removed. The existing
review's public pinned Hex artifact was read only as inert data.

Corrected actual Hex and Rebar exports, dependency resolution, prepared archive
export/restore, test/PG creation, offline compilation, both unchanged network
methods and all fresh-attempt isolation/cleanup remain pending independent
runtime evidence. Existing native, process, custody, customer, provider and GA
holds remain active. No missing or skipped gate is a pass.
