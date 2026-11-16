#!/usr/bin/env python3
"""Exact native-output source successor; row count is not a compiler/profile version."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = 'verification/plan-continuation-2026-11-07/source113-inspection-caller-r3'
TYPE = 'EXACT_NATIVE_OUTPUT_SOURCE121_AND_CALLER_SUCCESSOR'
MAX_BYTES = 8 * 1024 * 1024


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def regular(path):
    path = Path(path).absolute()
    for parent in [*reversed(path.parents), path]:
        need(not parent.is_symlink(), 'Symlink forbidden: ' + str(parent))
    info = path.stat()
    need(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_BYTES, 'Bounded regular file required')
    return path


def row(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def read(path):
    return regular(path).read_bytes()


def load_json(path):
    return json.loads(read(path), object_pairs_hook=unique)


def digest(files):
    return hashlib.sha256(''.join(p + '\0' + r['sha256'] + '\n'
                                  for p, r in sorted(files.items())).encode()).hexdigest()


def relative(name):
    need(type(name) is str and len(name) <= 1024 and '\\' not in name and '\0' not in name,
         'Bad relative path')
    p = Path(name)
    need(p.as_posix() == name and not p.is_absolute() and name not in ('', '.')
         and not any(v in ('.', '..', '.git') for v in p.parts), 'Bad relative path')
    return p


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, regular(path))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def check_rows(root, rows):
    need(type(rows) is dict and len(rows) <= 1024, 'Bounded owning rows required')
    for name, expected in rows.items():
        need(row(read(root / relative(name))) == expected, 'Owning bytes differ: ' + name)


def inverse121(binding, selected):
    transition = binding['native_output_transition']
    need(type(transition) is dict and set(transition) == {
        'schema', 'type', 'sourceBefore', 'sourceAfter', 'sourceCountBefore',
        'sourceCountAfter', 'changes', 'qualification', 'scope'}, 'Transition fields differ')
    need(type(transition['schema']) is int and transition['schema'] == 1
         and transition['type'] == TYPE
         and type(transition['sourceCountBefore']) is int and transition['sourceCountBefore'] == 119
         and type(transition['sourceCountAfter']) is int and transition['sourceCountAfter'] == 121
         and transition['qualification'] is False
         and transition['scope'] == 'public --output nativeSimulator development only; aggregate false',
         'Typed transition differs')
    need(type(selected) is dict and len(selected) == 121
         and digest(selected) == transition['sourceAfter'], 'Selected source121 differs')
    predecessor = dict(selected)
    changes = transition['changes']
    need(type(changes) is dict and len(changes) == 6, 'Exact six product changes required')
    need(set(changes) == {
        'cli/Sources/MixerBuild/AppleProject.swift',
        'cli/Sources/MixerBuild/NativeBuildOutput.swift',
        'cli/Sources/MixerBuild/NativeProductCapture.swift',
        'cli/Sources/MixerBuild/POSIXCommandControl.swift',
        'cli/Sources/MixerBuild/ProjectGenerator.swift',
        'cli/Sources/MixerCLI/main.swift'}, 'Product change roster differs')
    for name, change in changes.items():
        need(type(change) is dict and set(change) == {'before', 'after'}
             and selected.get(name) == change['after'], 'Native successor row differs: ' + name)
        if change['before'] is None:
            del predecessor[name]
        else:
            predecessor[name] = change['before']
    need(len(predecessor) == 119 and digest(predecessor) == transition['sourceBefore'],
         'Complete source119 inverse differs')
    need(predecessor == load_json(ROOT / OLD / 'current-source-inputs.json'),
         'Immutable source119 manifest differs')
    return predecessor


def admit():
    seal = load_json(HERE / 'seal.json')
    need(type(seal) is dict and set(seal) == {'schema', 'members', 'tree_sha256'}
         and type(seal['schema']) is int and seal['schema'] == 1, 'Successor seal fields differ')
    members = seal['members']
    check_rows(HERE, members)
    need(digest(members) == seal['tree_sha256'], 'Successor seal differs')
    observed = []
    for p in HERE.rglob('*'):
        name = p.relative_to(HERE).as_posix()
        if p.relative_to(HERE).parts[0] in {'control-scratch', '__pycache__'}:
            continue
        need(not p.is_symlink(), 'Shipping symlink forbidden')
        if p.is_file() and name != 'seal.json':
            observed.append(name)
    need(sorted(observed) == sorted(members), 'Unknown successor member')
    binding = load_json(HERE / 'binding.json')
    need(binding['type'] == TYPE and type(binding['schema']) is int and binding['schema'] == 1,
         'Binding type differs')
    need(all(value is False for value in binding['root_gates'].values())
         and set(binding['root_gates']) == {'manifest_fix', 'posix_scope', 'ordinary382',
             'independent_packet_review', 'explicit_successor_selection'}, 'Root gates differ')
    need(binding['adoption'] is False and binding['activation'] is False
         and binding['aggregate'] is False and binding['GA'] is False,
         'Development scope differs')
    selected = load_json(HERE / 'current-source-inputs.json')
    check_rows(ROOT, selected)
    owner = module('native121_owning_checker', ROOT / 'scripts/ci/check-android-generated-java.py')
    profile = owner.load_profile(ROOT)
    need(owner.source_inputs(profile) == selected, 'Owning source roster differs')
    predecessor = inverse121(binding, selected)
    need(binding['source'] == {'count': 121, 'sha256': digest(selected),
         'algorithm': 'sha256 of sorted path + NUL + file sha256 + newline; scripts/ci/check-android-generated-java.py:source_inputs',
         'manifest': 'current-source-inputs.json'}, 'Source metadata differs')
    # Preserve Pair21 and every historical transition byte-for-byte in the old authority.
    old_binding = load_json(ROOT / OLD / 'binding.json')
    need(binding['profile'] == old_binding['profile']
         and binding['renderer_pair21_transition'] == old_binding['renderer_pair21_transition'],
         'Pair21 selection differs')
    check_rows(ROOT, load_json(HERE / 'owning-closure.json'))
    check_rows(ROOT, load_json(HERE / 'caller-inputs.json'))
    check_rows(ROOT, binding['installed_bytes'])
    need(binding['ordinary_test']['path'] == 'cli/Tests/MixerBuildTests/NativeOutputAdmissionTests.swift'
         and binding['ordinary_test']['actual_self_contained_tests'] == 18,
         'Ordinary test reconciliation differs')
    need(not (ROOT / 'cli/Tests/MixerBuildTests/NativeProductCaptureTests.swift').exists()
         and not (ROOT / 'cli/Tests/MixerBuildTests/PublicNativeOutputTests.swift').exists(),
         'Campaign tests must not enter ordinary discovery')
    return binding, selected, predecessor


def legacy_view(binding, predecessor):
    legacy = module('native121_legacy_owner', ROOT / OLD / 'adopt_envelope.py')
    base = legacy.bind()
    original_regular, original_module = base.regular, base.module_at
    overlays = binding['predecessor_bytes']
    for name, entry in overlays.items():
        need(row(read(ROOT / relative(name))) == entry['after'], 'Changed caller/source differs')
        need(row(read(HERE / relative(entry['preimage']))) == entry['before'], 'Predecessor bytes differ')
    def old_regular(path):
        name = Path(path).relative_to(ROOT).as_posix() if Path(path).is_relative_to(ROOT) else None
        if name in overlays:
            return original_regular(HERE / overlays[name]['preimage'])
        return original_regular(path)
    def old_module(name, path):
        result = original_module(name, path)
        if Path(path) == ROOT / 'scripts/ci/check-android-generated-java.py':
            # The selected roster was just read and inverted, never a caller-supplied replacement.
            result.source_inputs = lambda profile: dict(predecessor)
        return result
    base.regular, base.module_at = old_regular, old_module
    return legacy, base


def verify(installed=False):
    binding, selected, predecessor = admit()
    legacy, base = legacy_view(binding, predecessor)
    historical = base.verify(installed)
    return {'schema': 1, 'type': TYPE, 'source_count': 121, 'source_sha256': digest(selected),
            'predecessor_source_count': 119, 'predecessor_source_sha256': digest(predecessor),
            'profile': binding['profile'], 'historical119': historical,
            'root_gates': binding['root_gates'], 'aggregate': False, 'adoption': False,
            'activation': False, 'GA': False, 'holdsReleased': False}


def prepare_predecessor(out):
    binding, selected, predecessor = admit()
    out = Path(out).absolute()
    need(not out.exists() and not out.is_symlink(), 'Fresh predecessor directory required')
    # Full exact owning closure, including old helper/schema/workflow closure; no active docs.
    files = dict(load_json(HERE / 'owning-closure.json'))
    files.update(load_json(HERE / 'caller-inputs.json'))
    files.update(selected)
    files.update(binding['installed_bytes'])
    before = binding['predecessor_bytes']
    prepared = {}
    for name in files:
        if name in binding['new_paths']:
            continue
        raw = read(HERE / before[name]['preimage']) if name in before else read(ROOT / name)
        prepared[name] = raw
    need(len(prepared) <= 1024 and sum(map(len, prepared.values())) <= 64*1024*1024,
         'Predecessor projection budget exceeded')
    for p in [*reversed(out.parents), out.parent]:
        need(not p.is_symlink(), 'Predecessor parent symlink')
    out.mkdir(parents=True, mode=0o700)
    for name, raw in prepared.items():
        path = out / relative(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    for path in (OLD, 'verification/envelope-rust-1991-default-ci-adoption'):
        (out / path / 'control-scratch').mkdir(exist_ok=True)
    return {'files': len(prepared), 'bytes': sum(map(len, prepared.values())),
            'source119': digest(predecessor), 'out': str(out)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('verify')
    p.add_argument('--workflow-installed', action='store_true')
    p = sub.add_parser('prepare-predecessor')
    p.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('run')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--rustc', required=True)
    args = parser.parse_args()
    if args.command == 'verify':
        print(json.dumps(verify(args.workflow_installed), sort_keys=True))
    elif args.command == 'prepare-predecessor':
        print(json.dumps(prepare_predecessor(args.out), sort_keys=True))
    else:
        binding, _, predecessor = admit()
        legacy, base = legacy_view(binding, predecessor)
        old_verify = base.verify
        def both(installed=False):
            # Fresh selected bytes plus all original guards before and after fixture dispatch.
            admit()
            result = old_verify(installed)
            return dict(result, native_output_source121=digest(load_json(HERE/'current-source-inputs.json')))
        base.verify = both
        return legacy.run_fixture(base, args.out, args.rustc)
    return 0


if __name__ == '__main__':
    sys.exit(main())
