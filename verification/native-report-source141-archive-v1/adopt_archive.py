#!/usr/bin/env python3
"""Admit the reviewed native-report archive owner and reconstruct its predecessor."""

import argparse
import hashlib
import importlib.util
import json
import stat
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREVIOUS = Path('verification/sdk-feature-ui-source141-v1')
PREVIOUS_SEAL_SHA256 = '06952f22a0a4fc6b2272e7f545abb9e46ec526372abf5e2244c6599e3a6246ed'
TYPE = 'EXACT_NATIVE_REPORT_ARCHIVE_SOURCE141_SUCCESSOR'
CLOSEOUT_SOURCE_SHA256 = '7e04cab7419cf65db0a8ad70a97f6ea94b1cb6db882f6c7ec724e24d170a2b28'
PAIR23_SOURCE_SHA256 = 'f68f02c92c93947becf9e29b7eeef43b88313f13e7f7c915fdf47f902f4f81cd'
RENDERER = 'app/src/dev/mixer/android/NativeAppearanceViewsV2.java'
CLOSEOUT_SOURCE_CHANGES = frozenset((
    'cli/Sources/MixerBuild/BuildInputSnapshot.swift',
    'cli/Sources/MixerBuild/Configuration.swift',
    'cli/Sources/MixerBuild/NativeProductCapture.swift',
    'cli/Sources/MixerBuild/ProjectGenerator.swift',
    'updates/Sources/MixerUpdates/VerifierV3.swift',
    'updates/Sources/MixerUpdateTool/main.swift',
))
RENDERER_SOURCE_CHANGES = {
    'native/android/' + RENDERER,
    'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift',
    'cli/Sources/MixerBuild/Resources/android-build.py',
    'scripts/ci/check-android-generated-java.py',
}
SOURCE_CHANGES = CLOSEOUT_SOURCE_CHANGES | RENDERER_SOURCE_CHANGES
ADDITIONS = {
    'cli/build-tests/test_public_export.py',
    'native/android/tests/CollapsedEditorFrameHostTests.java',
    'updates/verification/verify-cli.py',
}
JAVA = 'verification/plan-continuation-2026-11-07/generated-java-ci-integration/'
CHANGES = SOURCE_CHANGES | ADDITIONS | {
    'cli/Tests/MixerBuildTests/BuildTests.swift',
    'cli/Tests/MixerBuildTests/NativeOutputAdmissionTests.swift',
    'cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift',
    'cli/Tests/MixerBuildTests/GeneratedPublicAndroidV4Tests.swift',
    'cli/build-tests/current_android_profile.py',
    'native/android/tests/NativeOwnerV2ConcreteHostLeaves/android/view/View.java',
    'native/android/tests/private-owner-barrier-bindings.json',
    'native/android/tests/private-owner-barrier-map.json',
    'native/android/tests/run-public-surface-host.py',
    '.github/workflows/verify.yml',
    'updates/README.md',
    JAVA + 'bootstrap.py',
    JAVA + 'test_bootstrap.py',
    JAVA + 'test_sparse_checkout.py',
}
STARTER_SOURCE_CHANGES = {
    'cli/Sources/MixerBuild/AndroidProject.swift',
    'cli/Sources/MixerBuild/ProjectGenerator.swift',
}
STARTER_CHANGES = STARTER_SOURCE_CHANGES | {'cli/build-tests/test_public_export.py'}
MEMBERS = {'adopt_archive.py', 'binding.json', 'current-source-inputs.json'} | {
    'predecessor-bytes/' + name for name in CHANGES - ADDITIONS
} | {
    'pair23-predecessor-bytes/' + name for name in STARTER_CHANGES
}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def read_predecessor_member(path):
    limit = 256 * 1024
    metadata = path.lstat()
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_size <= limit,
            'Bounded ordinary Source141 member required: ' + str(path))
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, 'Source141 admission member exceeds read budget')
    return raw


def load_predecessor():
    base = ROOT / PREVIOUS
    for directory in (base.parent, base):
        require(stat.S_ISDIR(directory.lstat().st_mode),
                'Source141 authority directory required: ' + str(directory))
    raw = read_predecessor_member(base / 'seal.json')
    require(hashlib.sha256(raw).hexdigest() == PREVIOUS_SEAL_SHA256,
            'Source141 predecessor seal differs')
    seal = json.loads(raw)
    entry = base / 'adopt_sdk.py'
    raw = read_predecessor_member(entry)
    require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} ==
            seal['members']['adopt_sdk.py'], 'Source141 predecessor entry differs')
    spec = importlib.util.spec_from_file_location('historical_source141_authority', entry)
    previous = importlib.util.module_from_spec(spec)
    # Execute the exact verified bytes, with the original module path.
    exec(compile(raw, str(entry), 'exec'), previous.__dict__)
    previous.closed_members(base, {*seal['members'], 'seal.json'})
    previous.check_rows(base, seal['members'])
    return previous, seal


def install_inputs():
    previous, old_seal = load_predecessor()
    seal = previous.load(HERE / 'seal.json')
    require(set(seal) == {'schema', 'members', 'tree_sha256'} and
            type(seal['schema']) is int and seal['schema'] == 1 and
            set(seal['members']) == MEMBERS and
            previous.digest(seal['members']) == seal['tree_sha256'],
            'Archive authority seal differs')
    previous.closed_members(HERE, {*MEMBERS, 'seal.json'})
    previous.check_rows(HERE, seal['members'])
    binding = previous.load(HERE / 'binding.json')
    require(set(binding) == {'schema', 'type', 'source', 'profile', 'predecessor_binding',
                             'changes', 'renderer_transition', 'starter_lock_transition'} and
            type(binding['schema']) is int and binding['schema'] == 1 and binding['type'] == TYPE and
            binding['predecessor_binding'] == (PREVIOUS / 'binding.json').as_posix() and
            set(binding['changes']) == CHANGES, 'Archive binding or change roster differs')

    original = ROOT / PREVIOUS
    current = previous.load(HERE / 'current-source-inputs.json')
    historical_source = previous.load(original / 'current-source-inputs.json')
    historical_binding = previous.load(original / 'binding.json')
    historical = previous.load(original / 'historical-inputs.json')
    caller = previous.load(original / 'caller-inputs.json')
    owning = previous.load(original / 'owning-closure.json')
    effective = {**owning, **caller, **historical_source}
    pair23_source = dict(historical_source)
    starter = binding['starter_lock_transition']
    require(set(starter) == {'sourceBefore', 'sourceAfter', 'changes'} and
            set(starter['changes']) == STARTER_CHANGES, 'Starter lock change roster differs')
    pair23_preimages = {}
    for name, change in starter['changes'].items():
        require(set(change) == {'before', 'after'} and change['before'] != change['after'],
                'Starter lock transition differs: ' + name)
        raw = previous.read(HERE / 'pair23-predecessor-bytes' / name)
        require(previous.row(raw) == change['before'], 'Pair23 owner preimage differs: ' + name)
        pair23_preimages[name] = raw

    preimages = {}
    for name, change in binding['changes'].items():
        require(set(change) == {'before', 'after', 'mode'} and
                (name not in effective if name in ADDITIONS else name in effective) and
                change['before'] == effective.get(name), 'Predecessor owner binding differs: ' + name)
        path = ROOT / name
        raw = pair23_preimages[name] if name in pair23_preimages else previous.read(path)
        require(previous.row(raw) == change['after'], 'Pair23 archive owner differs: ' + name)
        require(type(change['mode']) is int and change['mode'] in (0o644, 0o755) and
                stat.S_IMODE(path.stat().st_mode) == change['mode'],
                'Installed archive owner mode differs: ' + name)
        if name not in ADDITIONS:
            raw = previous.read(HERE / 'predecessor-bytes' / name)
            require(previous.row(raw) == change['before'], 'Archive owner preimage differs: ' + name)
            preimages[name] = (raw, change['mode'])
        effective[name] = change['after']
        if name in SOURCE_CHANGES:
            pair23_source[name] = change['after']
    require(previous.digest(pair23_source) == starter['sourceBefore'] == PAIR23_SOURCE_SHA256 and
            all(pair23_source[n] != historical_source[n] for n in SOURCE_CHANGES),
            'Pair23 source inverse differs')
    closeout = {**pair23_source, **{name: historical_source[name] for name in RENDERER_SOURCE_CHANGES}}
    require(previous.digest(closeout) == CLOSEOUT_SOURCE_SHA256, 'CLI closeout source differs')

    expected_source = dict(pair23_source)
    for name, change in starter['changes'].items():
        require(effective[name] == change['before'], 'Pair23 predecessor binding differs: ' + name)
        effective[name] = change['after']
        if name in STARTER_SOURCE_CHANGES:
            expected_source[name] = change['after']
        if name not in CHANGES:
            require(stat.S_IMODE((ROOT / name).stat().st_mode) == 0o644,
                    'Installed starter lock source mode differs: ' + name)
            preimages[name] = (pair23_preimages[name], 0o644)
    require(current == expected_source and
            starter['sourceAfter'] == binding['source']['sha256'] and
            len(current) == 141 and binding['source'] == {
                'count': len(current), 'sha256': previous.digest(current), 'manifest': 'current-source-inputs.json'
            }, 'Starter lock source transition differs')
    previous.check_rows(ROOT, effective)
    owner = previous.module('native_archive_actual_collector', ROOT / previous.OWNER)
    profile = owner.load_profile(ROOT)
    pair22 = historical_binding['sdk_transition']['profileAfter']
    adapter_files = {**pair22['adapter_files'], RENDERER: current['native/android/' + RENDERER]}
    expected_profile = {**pair22, 'id': 'mixer.android-source-pair.23', 'adapter_files': adapter_files,
                        'adapter_compatibility_sha256': previous.digest(adapter_files)}
    require(binding['renderer_transition'] == {
                'sourceBefore': CLOSEOUT_SOURCE_SHA256,
                'sourceAfter': PAIR23_SOURCE_SHA256,
                'profileAfter': expected_profile,
            } and profile == expected_profile and previous.profile_summary(profile) == binding['profile'],
            'Archive renderer successor profile differs')
    selector_path = ROOT / 'cli/build-tests/current_android_profile.py'
    selector = previous.module('native_archive_current_selector', selector_path)
    require(selector.load_current_profile(ROOT) == profile, 'Current renderer selector differs')
    require(owner.source_inputs(profile) == current, 'Actual archive owning source map differs')

    material = {}
    history_paths = set(historical) | (effective.keys() - ADDITIONS) | {
        (PREVIOUS / name).as_posix() for name in (*old_seal['members'], 'seal.json')
    }
    total = 0
    for name in sorted(history_paths):
        if name in preimages:
            raw, mode = preimages[name]
        else:
            path = ROOT / previous.relative(name)
            raw, mode = previous.read(path), stat.S_IMODE(path.stat().st_mode)
        total += len(raw)
        require(total <= 64 * 1024 * 1024, 'Source141 restoration copy budget exceeded')
        material[name] = (raw, mode)
    return binding, current, material


def restore(out, material):
    out = Path(out).absolute()
    require(not out.exists() and not out.is_symlink(), 'Fresh Source141 output required')
    require(not any(p.is_symlink() for p in out.parents), 'Source141 output ancestry symlink')
    out.mkdir(mode=0o700)
    for name, (raw, mode) in material.items():
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        path.chmod(mode)
    spec = importlib.util.spec_from_file_location('restored_source141_authority',
                                                  out / PREVIOUS / 'adopt_sdk.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, module.admit()


def admit():
    binding, selected, material = install_inputs()
    with tempfile.TemporaryDirectory(prefix='native-archive-source141-') as scratch:
        _, (historical, _, source127) = restore(Path(scratch).resolve() / 'source141', material)
    return {**binding, 'sdk_transition': historical['sdk_transition']}, selected, source127


def verify(installed=False):
    binding, selected, _ = admit()
    return {'schema': 1, 'type': TYPE, 'source_count': len(selected),
            'source_sha256': binding['source']['sha256'], 'profile': binding['profile'],
            'predecessor_pair23_source141_sha256': binding['starter_lock_transition']['sourceBefore'],
            'predecessor_closeout_source141_sha256': binding['renderer_transition']['sourceBefore'],
            'predecessor_source141_sha256': binding['sdk_transition']['sourceAfter'],
            'predecessor_source127_sha256': binding['sdk_transition']['sourceBefore'],
            'adoption': False, 'activation': False, 'aggregate': False, 'GA': False, 'holdsReleased': False}


def prepare_source141(out):
    _, _, material = install_inputs()
    _, (binding, _, _) = restore(out, material)
    return {'source141': binding['source']['sha256'], 'files': len(material),
            'source127': binding['sdk_transition']['sourceBefore'], 'out': str(out)}


def prepare_predecessor(out):
    _, _, material = install_inputs()
    with tempfile.TemporaryDirectory(prefix='native-archive-source141-') as scratch:
        previous, _ = restore(Path(scratch).resolve() / 'source141', material)
        return previous.prepare_predecessor(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    verify_parser = commands.add_parser('verify')
    verify_parser.add_argument('--workflow-installed', action='store_true')
    for name in ('prepare-source141', 'prepare-predecessor'):
        commands.add_parser(name).add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'verify':
        result = verify(args.workflow_installed)
    elif args.command == 'prepare-source141':
        result = prepare_source141(args.out)
    else:
        result = prepare_predecessor(args.out)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
