# Identity network execution amendment v2

This packet implements the root-selected tooling-tmpfs correction after the
v1 image passed preparation prerequisites but bootstrap failed executing Rebar.
It authors source and Python pure controls only. It makes no commit/push or
runtime acceptance decision, and it does not change product/test/fixture code,
images, dependency pins, capabilities, memory/CPU/PID limits or PostgreSQL mounts.

The final immutable operational metadata is only `metadata/`:

| Binding | SHA256 |
| --- | --- |
| `execution-amendment.json` | `b447fe5919c4e73d86aee4da707570127de2c35ecdae5a7b90b0163eb9bc436c` |
| Packet canonical file-map root | `0e35cd6dcc1685b16745def4fe0217fc60e5d703c95a5cddbfd2409381c63b6d` |
| Exact `packet-manifest.json` bytes | `dcac91f5cae0a2495f79448a76098975edc18db0ce96a1e769106244a0cf8061` |

The metadata packet seals 16 files. The outer packet separately seals source,
commands, failures and implementation evidence without self-reference. Its
`implementation/draft-before-transfer/` snapshot is historical draft evidence;
it has no operational authority and is not checked out by the runtime workflow.

The closed amendment binds the exact original contract and v1 amendment roots,
raw v1 amendment/manifest bytes, fixed old/new tmpfs tables, the workspace sum,
all current image/tool/CA/product/PG/bootstrap/resource/capability invariants,
the actual failed-run proof and the narrowly defined Rebar transfer. No overlay
map can authorize additional execution, capacity, paths, mounts or capabilities.
The collector retains all three full metadata namespaces in
`selected-contract-metadata.tar` and validates all seals before image operations.
The workflow's push/PR filters and sparse metadata checkout include v2.

Both preparation and test containers now use:

| Mount | Bytes | Flags/mode |
| --- | --- | --- |
| `/workspace` | 1,006,632,960 | `rw,nosuid,nodev,noexec,mode=0755` |
| `/workspace/tooling` | 67,108,864 | `rw,nosuid,nodev,exec,mode=0755` |
| `/tmp` | 67,108,864 | `rw,nosuid,nodev,noexec,mode=1777` |

The workspace and tooling capacities total the original 1,073,741,824 bytes.
The test `/run` declaration stays unchanged and must actually be `noexec`.
The 64 MiB tooling capacity is a selected finite bound; its sufficiency for
complete bootstrap/dependency work remains a runtime question. This author
does not enlarge it based on source estimates.

The helper `collector-mounts.exs` runs through image-supplied Elixir in each exact
owned preparation/test container after copy-in. It opens only that container's
`/proc/self/mountinfo`, reads at most 65537 bytes and refuses anything over
65536 bytes, filters only the selected paths and their descendants, and records
the selected raw lines, actual modes and a hash/size of the bounded read. It
starts no child process and performs no mount operation. The Python consumer
independently parses the selected lines and requires actual tmpfs, `rw`,
`nosuid`, `nodev`, exact sizes, correct modes, workspace/tmp/run `noexec`, and
executable tooling. Only the exact selected tooling child mount beneath
workspace is permitted; extra descendants, duplicate mounts or wrong tooling
parent mount ID fail. Existing Docker inspection guards remain in force.

The evidence basis is run `40740023326`, artifact `12837649788`, delivery
`cc350d3303ca71c5d57e87846f6a61304b658fa7`. Its artifact file-map root is
`616274ea3bccd45a7b506a0b71de1016b004cbe55e9ca5f3da9fb2cfb9d394bf`, and retained
ZIP SHA256 is `932f877ed0fc8cf8ad9457e0ba1b4888ff7bd5a58762b86975f6e887f9673231`.
The fresh independent Astra review accepted actual preparation seven-tool,
VM, OpenSSL and CA150 observations and exact owned cleanup for that attempt.
Those raw prerequisite bytes and their original-path reference are retained
under `metadata/proof/runtime/`. The new collector still requires fresh actual
prerequisite and mount results on every attempt; history supplies no new pass.

Command 22 failed with EACCES directly spawning
`/workspace/tooling/rebar3 --version`. Its original 434-byte stderr, exact
command record and false stdout/stderr-complete flags are retained without
rewriting. No structured complete bootstrap receipt or actual mountinfo existed.
The [exact Docker 28.0.4 source](https://github.com/moby/moby/blob/v28.0.4/daemon/oci_linux.go)
supplies `noexec` for tmpfs and its
[vendored mount option merger](https://github.com/moby/moby/blob/v28.0.4/vendor/github.com/moby/sys/mount/flags_unix.go)
lets a later explicit `exec` override that default. This supports the cause as
an inference, not an observed prior kernel mount fact. The
[exact Mix 1.20.4 source](https://github.com/elixir-lang/elixir/blob/v1.20.4/lib/mix/lib/mix/rebar.ex)
also uses direct Unix Rebar invocation; bootstrap-only escript invocation would
leave dependency compilation affected. Exact official source responses are
retained, each fetched within 25 seconds and 256 KiB. No image/tool was fetched,
installed, built or executed here.

Source review identified one necessary consequence of the nested tooling
mount: the old File.rename transfer from `/workspace/downloads/rebar3` to
`/workspace/tooling/rebar3` would cross filesystems. Root selected an exclusive,
bounded verified copy at those unchanged paths. The helper requires the source
regular file and complete source bytes within 16 MiB, creates the absent target
exclusively, requires complete write/close, rechecks target exact size and SHA512
before chmod/direct execution, then removes only the owned download. A copy,
close, target hash or removal failure remains a failed attempt. There is no
rename fallback, alternate path, package install or broader workspace execution.
The observed transfer receipt must join the verified download and target byte
counts/checksum with exclusive-create, close and removal facts before the
collector accepts bootstrap. Existing actual Hex/Rebar version checks remain.

`implementation/canonical.diff` and before/after snapshots cover four canonical
files. Final source bindings have canonical tree SHA256
`65b12100be7470e42761042bfe572ce799952bd04c3d40dba3042d1224fbdb5c`.
The final command `python3 -B hosted/scripts/test_identity_network_collector.py`
passed all 103 controls in 0.523 seconds on Python 3.14.8, within its unchanged
50-second alarm and global child-process/socket guards. The 19 new controls
cover immutable execution selection/seals, wrong sums/paths/capacities/caps,
source-preserved invariants, actual mount options/sizes/hierarchy/absence,
wrong declared tmpfs, direct collector gating, and incomplete/incorrect Rebar
transfer receipts. Eighty-three prior v1 test bodies are unchanged. One v1
orchestration fixture represents the new earlier mount gate/v2 metadata while
preserving its prerequisite-refusal and no-bootstrap assertions. All original
68 test bodies remain byte-for-byte unchanged. The prepared-archive fixture
now carries the separately hashed mount helper.

The first 99-control run retained one failure: the new strict mutation control
showed that appending whitespace to a canonical file-map seal was accepted.
The v2 validator now additionally pins exact packet-manifest bytes; the next
99-control run passed. After the transfer correction, 103 controls passed,
then the final unchanged-source run passed again. All logs and the prior draft
are retained. No prior runtime failure was removed or reclassified as a pass.

`implementation/verify-source.py` reads the 177 committed Git blobs and confirms
product digest `023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e`.
It rehashes the original 46-file contract, complete 110-file v1 packet and
71-file source review without changes. Source HEAD is
`cc350d3303ca71c5d57e87846f6a61304b658fa7`, tree
`07f2b0e23e58dd445e2731930fc66b00ed49ec2e`. `THIRD_PARTY.yml` remains unchanged,
as do protected live hosted workflow SHA256 `fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57`
and browser-auth store SHA256 `8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299`.
The protected dirty live store is separate from committed product source.

No local Docker, compiler, guest, PG, product, hosted replay, PID/process
inventory, held custody harness, native/UI/capture, credentials, publication,
commit or push action occurred. Pure-test TemporaryDirectories were owned and
automatically removed. Fresh actual mount policy, complete bootstrap/transfer,
locked dependency preparation, offline compilation, both unchanged network
methods and all new-attempt isolation/cleanup remain pending. All prior native,
process, custody, provider, customer and GA holds remain in force. Source and
pure controls establish none of those runtime passes.
