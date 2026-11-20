#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
pin=2e8f505f789c97c0f1330c611f6b0378daabf3d5
candidate=b55788e0b050533f724547a812871d6ad8a7fd21
producer_fix=41d46e475bc1e9ab88beca6338b1b8af8778309a
archive=verification/native-report-source141-archive-v1
verify=.github/workflows/verify.yml
git diff --exit-code "$candidate" -- hosted .github/workflows \
    verification/identity-network-current-source-v55 "$archive"
git diff --exit-code 00aa86d374 "$pin" -- hosted console .github/workflows \
    tests/integration/managed-android-local-linux-pair25

scratch=$(mktemp -d /private/tmp/mx55.XXXXXXXX)
trap 'rm -rf -- "$scratch"' EXIT
export TMPDIR="$scratch"
unset MIXER_PAIR25_BUNDLE

for optimization in '' -O; do
    mode=normal
    if [[ -n "$optimization" ]]; then mode=optimized; fi
    python3 -B ${optimization:+-O} hosted/scripts/test-identity-network.py --check-source
    python3 -B ${optimization:+-O} hosted/scripts/test_identity_network_collector.py \
        WorkspaceSourceCutoverControls WorkflowSparseSourceControls CurrentCLISelectionControls \
        CollectorMethodWiringControls.test_collect_requires_actual_prepare_result_before_bootstrap
    python3 -I -B -S ${optimization:+-O} "$archive/adopt_archive.py" verify --workflow-installed
    python3 -I -B -S ${optimization:+-O} "$archive/adopt_archive.py" prepare-source141 --out "$scratch/source141-$mode"
    python3 -I -B -S ${optimization:+-O} \
        verification/plan-continuation-2026-11-07/generated-java-ci-integration/test_sparse_checkout.py
    cmp <(git show "$pin:$verify") "$archive/hosted-v55-predecessor-bytes/$verify"
    printf '%s  %s\n' b283a00fc9a7ca1b900306d3a4226e182e0ba966014efe0d3427207806f0c69e \
        "$scratch/source141-$mode/$verify" | shasum -a 256 -c
done
cmp "$scratch/source141-normal/$verify" "$scratch/source141-optimized/$verify"

python3 -B - "$pin" "$candidate" "$producer_fix" <<'PY'
import hashlib
import json
from pathlib import Path
import subprocess
import sys

pin, candidate, fix = sys.argv[1:]
v54 = Path('verification/identity-network-current-source-v54')
v55 = Path('verification/identity-network-current-source-v55')

def blob(revision, path):
    return subprocess.check_output(['git', 'show', f'{revision}:{path}'])

def row(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

old = json.loads(blob(pin, v54 / 'selected-source-manifest.json'))
new = json.loads(blob(candidate, v55 / 'selected-source-manifest.json'))
selection = json.loads(blob(candidate, v55 / 'selection.json'))
restored = {name: blob(candidate, name) for name in new}
if {name: row(raw) for name, raw in restored.items()} != new:
    raise SystemExit('Candidate bytes differ from v55 manifest')
for name, change in selection['exact_delta'].items():
    if restored[name] != blob(fix, name):
        raise SystemExit(f'Producer bytes differ: {name}')
    if change['before'] is None:
        del restored[name]
    else:
        restored[name] = blob(candidate, v55 / 'preimages' / name)
if {name: row(raw) for name, raw in restored.items()} != old:
    raise SystemExit('Restored v54 roster or digests differ')
for name, raw in restored.items():
    if raw != blob(pin, name):
        raise SystemExit(f'Public v54 preimage differs: {name}')
print(f'Restored {len(restored)} v54 files byte for byte')
PY

mkdir -p "$scratch/tree" "$scratch/hex/packages/hexpm" "$scratch/mix/elixir/1-20-otp-29"
git archive "$candidate" hosted services/protocol/testdata \
    cli/Sources/MixerBuild/Resources/android-build.py tests/integration/managed-android-local-linux-pair25 |
    tar -xf - -C "$scratch/tree"
(
    cd "$scratch/tree/hosted"
    python3 -B scripts/test_native_artifact_worker.py -v
    python3 -B -O scripts/test_native_artifact_worker.py -v

    export MIX_HOME="$scratch/mix" HEX_HOME="$scratch/hex" MIX_ENV=test
    export MIX_ARCHIVES="${MIX_ARCHIVES:-$HOME/.mix/archives}"
    export MIX_DEPS_PATH="$PWD/deps" MIX_BUILD_PATH="$PWD/_build"
    unset HEX_OFFLINE
    cp "${MIXER_V55_REBAR3:-$HOME/.mix/elixir/1-20-otp-29/rebar3}" \
        "$MIX_HOME/elixir/1-20-otp-29/rebar3"
    elixir -pa "$MIX_ARCHIVES/hex-2.5.1/hex-2.5.1/ebin" -e '
      :ok = Mix.start()
      {:ok, _} = Application.ensure_all_started(:hex)
      {lock, _} = Code.eval_file("mix.lock")
      21 = map_size(lock)
      Enum.each(lock, fn {_key, {:hex, name, version, _, _, _, "hexpm", expected}} ->
        archive = "#{name}-#{version}.tar"
        source = System.get_env("MIXER_V55_HEX_PACKAGES", Path.expand("~/.hex/packages/hexpm"))
        raw = File.read!(Path.join(source, archive))
        ^expected = :crypto.hash(:sha256, raw) |> Base.encode16(case: :lower)
        File.write!(Path.join([System.fetch_env!("HEX_HOME"), "packages", "hexpm", archive]), raw, [:exclusive])
      end)
      packages = Enum.flat_map(lock, fn {_key, {:hex, name, _, _, _, dependencies, repo, _}} ->
        [{repo, Atom.to_string(name)} | Enum.map(dependencies, fn {_app, _req, opts} ->
          {Keyword.fetch!(opts, :repo), opts |> Keyword.fetch!(:hex) |> Atom.to_string()}
        end)]
      end) |> Enum.uniq()
      :ok = Hex.Registry.Server.open()
      :ok = Hex.Registry.Server.prefetch(packages)
      Enum.each(packages, fn {repo, name} -> {:ok, [_ | _]} = Hex.Registry.Server.versions(repo, name) end)
      :ok = Hex.Registry.Server.close()
      IO.puts("Verified 21 Hex archives and warmed #{length(packages)} registry entries")
    '
    export HEX_OFFLINE=1
    mix deps.get --check-locked
    mix test test/mixer_hosted/builds/native_development_dispatch_test.exs --seed 0 --trace
    cmp mix.lock <(git -C "$OLDPWD" show "$candidate:hosted/mix.lock")
)
python3 scripts/check-verification-artifacts.py
