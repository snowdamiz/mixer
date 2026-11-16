#!/usr/bin/env python3
"""Typed source126 development admission, with exact immutable121 reconstruction."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREVIOUS = 'verification/native-output-source121-v1'
TYPE = 'EXACT_NATIVE_REPORT_SOURCE126_AND_CALLER_SUCCESSOR'
GATES = {'ordinary_composition', 'independent_packet_review', 'explicit_successor_selection'}
MAX_BYTES = 8 * 1024 * 1024
PRODUCTS = {'cli/Sources/MixerBuild/' + p for p in (
    'NativeBuildOutput.swift', 'ResourceInventoryProduct.swift', 'BuildInputSnapshot.swift',
    'SBOMProduct.swift', 'SamePublicBuildSBOM.swift', 'SamePublicBuildProvenance.swift')}


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def relative(name):
    need(type(name) is str and len(name) <= 1024 and '\\' not in name and '\0' not in name,
         'Invalid relative path')
    p = Path(name)
    need(p.as_posix() == name and not p.is_absolute() and name not in ('', '.')
         and not any(v in ('.', '..', '.git') for v in p.parts), 'Invalid relative path')
    return p


def regular(path):
    p = Path(path).absolute()
    for ancestor in [*reversed(p.parents), p]:
        need(not ancestor.is_symlink(), 'Symlink forbidden: ' + str(ancestor))
    st = p.stat()
    need(stat.S_ISREG(st.st_mode) and st.st_size <= MAX_BYTES, 'Bounded regular file required')
    return p


def read(path):
    return regular(path).read_bytes()


def row(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def load_json(path):
    return json.loads(read(path), object_pairs_hook=unique)


def digest(rows):
    return hashlib.sha256(''.join(p + '\0' + r['sha256'] + '\n'
                                  for p, r in sorted(rows.items())).encode()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, regular(path))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def source_input_path(name):
    p = relative(name)
    need('__pycache__' not in p.parts and p.suffix.lower() not in {'.pyc', '.pyo'},
         'Derived Python cache is not a source input: ' + name)
    return p


def check_rows(root, rows):
    need(type(rows) is dict and len(rows) <= 2048, 'Bounded rows required')
    paths = {name: source_input_path(name) for name in rows}
    for name, expected in rows.items():
        need(row(read(root / paths[name])) == expected, 'Owning bytes differ: ' + name)


def closed_members(root, members):
    """Exact authority only; excluded scratch directories are never descended."""
    allowed = set(members)
    directories = {p.as_posix() for name in allowed for p in Path(name).parents if p != Path('.')}
    observed, folders = set(), set()
    remaining = len(allowed) + len(directories) + 2
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    def walk(fd, prefix=''):
        nonlocal remaining
        with os.scandir(fd) as entries:
            for entry in entries:
                remaining -= 1
                need(remaining >= 0, 'Authority membership budget exceeded')
                name = prefix + entry.name
                scratch = not prefix and name in {'control-scratch', '__pycache__'}
                need(scratch or name in allowed or name in directories,
                     'Unknown authority member: ' + name)
                mode = entry.stat(follow_symlinks=False).st_mode
                if scratch or name in directories:
                    need(stat.S_ISDIR(mode), 'Authority directory required')
                    if not scratch:
                        folders.add(name)
                        child = os.open(entry.name, flags, dir_fd=fd)
                        try:
                            walk(child, name + '/')
                        finally:
                            os.close(child)
                else:
                    need(stat.S_ISREG(mode), 'Authority regular file required')
                    observed.add(name)
    fd = os.open(root, flags)
    try:
        walk(fd)
    finally:
        os.close(fd)
    need(observed == allowed and folders == directories, 'Authority membership differs')


def inverse126(binding, selected):
    t = binding['report_transition']
    need(type(t) is dict and set(t) == {'schema', 'type', 'sourceBefore', 'sourceAfter',
        'sourceCountBefore', 'sourceCountAfter', 'changes', 'qualification', 'scope'},
        'Transition fields differ')
    need(type(t['schema']) is int and t['schema'] == 1 and t['type'] == TYPE
         and type(t['sourceCountBefore']) is int and t['sourceCountBefore'] == 121
         and type(t['sourceCountAfter']) is int and t['sourceCountAfter'] == 126
         and t['qualification'] is False and t['scope'] == 'verified_subset; aggregate and GA false',
         'Typed source126 transition differs')
    need(type(selected) is dict and len(selected) == 126 and digest(selected) == t['sourceAfter'],
         'Selected source126 differs')
    need(type(t['changes']) is dict and set(t['changes']) == PRODUCTS, 'Exact six products required')
    previous = dict(selected)
    for name, change in t['changes'].items():
        need(type(change) is dict and set(change) == {'before', 'after'}
             and selected.get(name) == change['after'], 'Selected product differs')
        if change['before'] is None:
            del previous[name]
        else:
            previous[name] = change['before']
    need(len(previous) == 121 and digest(previous) == t['sourceBefore']
         == '71f1667f189ba4c4e2d7d2b89fd0aca2c37cc57f0113db0ed716fe55a3d06cfa'
         and previous == load_json(ROOT / PREVIOUS / 'current-source-inputs.json'),
         'Exact immutable source121 inverse differs')
    return previous


def admit():
    seal = load_json(HERE / 'seal.json')
    need(set(seal) == {'schema', 'members', 'tree_sha256'} and type(seal['schema']) is int
         and seal['schema'] == 1 and digest(seal['members']) == seal['tree_sha256'], 'Seal differs')
    closed_members(HERE, {*seal['members'], 'seal.json'})
    check_rows(HERE, seal['members'])
    b = load_json(HERE / 'binding.json')
    need(set(b) == {'schema', 'type', 'source', 'profile', 'renderer_pair21_transition',
        'report_transition', 'root_gates', 'adoption', 'activation', 'aggregate', 'GA',
        'ordinary_test', 'predecessor_bytes', 'new_paths', 'installed_bytes', 'limitations',
        'predecessor_authority', 'frozen_composition'}, 'Binding fields differ')
    need(type(b['schema']) is int and b['schema'] == 1 and b['type'] == TYPE, 'Binding type differs')
    need(set(b['root_gates']) == GATES and all(v is False for v in b['root_gates'].values())
         and all(b[k] is False for k in ('adoption', 'activation', 'aggregate', 'GA')), 'Root scope differs')
    selected = load_json(HERE / 'current-source-inputs.json')
    check_rows(ROOT, selected)
    owner = module('report126_owning_checker', ROOT / 'scripts/ci/check-android-generated-java.py')
    need(owner.source_inputs(owner.load_profile(ROOT)) == selected, 'Owning production roster differs')
    previous = inverse126(b, selected)
    need(b['source'] == {'count': 126, 'sha256': digest(selected), 'manifest': 'current-source-inputs.json',
        'algorithm': 'sha256 of sorted path + NUL + file sha256 + newline'}, 'Source metadata differs')
    old = load_json(ROOT / PREVIOUS / 'binding.json')
    need(b['profile'] == old['profile'] and b['renderer_pair21_transition'] == old['renderer_pair21_transition'],
         'Pair21 changed')
    pa = b['predecessor_authority']
    closed_members(ROOT / PREVIOUS, pa)
    check_rows(ROOT / PREVIOUS, pa)
    need(load_json(ROOT / PREVIOUS / 'seal.json')['tree_sha256'] ==
         '9744a3d5885b023f589fd46b1eca760e7d439055ce14f2c0ddcc5ff63db85773',
         'Current immutable121 seal changed')
    check_rows(ROOT, load_json(HERE / 'owning-closure.json'))
    check_rows(ROOT, load_json(HERE / 'caller-inputs.json'))
    check_rows(ROOT, b['installed_bytes'])
    test = b['ordinary_test']
    need(test['path'] == 'cli/Tests/MixerBuildTests/NativeOutputAdmissionTests.swift'
         and test['original_cases'] == 18 and test['added_unit_cases'] == 6
         and test['runtime_pass'] is False and test['path'] not in selected
         and row(read(ROOT / test['path'])) == test['identity'], 'Ordinary composition differs')
    return b, selected, previous


def legacy_view(binding, previous):
    legacy = module('report126_immutable121', ROOT / PREVIOUS / 'adopt_envelope.py')
    original_regular, original_module = legacy.regular, legacy.module
    overlays = binding['predecessor_bytes']
    for name, entry in overlays.items():
        need(row(read(ROOT / relative(name))) == entry['after'], 'Installed caller differs')
        need(row(read(HERE / relative(entry['preimage']))) == entry['before'], 'Exact121 preimage differs')
    def predecessor_regular(path):
        p = Path(path)
        name = p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else None
        if name in overlays:
            return original_regular(HERE / overlays[name]['preimage'])
        return original_regular(path)
    def predecessor_module(name, path):
        result = original_module(name, path)
        if Path(path) == ROOT / 'scripts/ci/check-android-generated-java.py':
            result.source_inputs = lambda profile: dict(previous)
        return result
    legacy.regular, legacy.module = predecessor_regular, predecessor_module
    original_legacy_view = legacy.legacy_view
    def nested_predecessor_view(binding121, predecessor119):
        historical, base = original_legacy_view(binding121, predecessor119)
        prior_regular = base.regular
        # The121 inverse has priority for rows already changed in that generation.
        # Newly changed callers (the sparse test) need the outer exact121 preimage.
        prior_changes = binding121['predecessor_bytes']
        def nested_regular(path):
            p = Path(path)
            name = p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else None
            if name in overlays and name not in prior_changes:
                return prior_regular(HERE / overlays[name]['preimage'])
            return prior_regular(path)
        base.regular = nested_regular
        return historical, base
    legacy.legacy_view = nested_predecessor_view
    return legacy


def verify(installed=False):
    b, selected, previous = admit()
    historical = legacy_view(b, previous).verify(installed)
    return {'schema': 1, 'type': TYPE, 'source_count': 126, 'source_sha256': digest(selected),
        'predecessor_source_count': 121, 'predecessor_source_sha256': digest(previous),
        'historical121': historical, 'root_gates': b['root_gates'], 'aggregate': False,
        'adoption': False, 'activation': False, 'GA': False, 'holdsReleased': False}


def prepare_predecessor(out):
    b, selected, previous = admit()
    out = Path(out).absolute()
    need(not out.exists() and not out.is_symlink(), 'Fresh predecessor directory required')
    for p in [*reversed(out.parents), out.parent]:
        need(not p.is_symlink(), 'Predecessor parent symlink')
    files = dict(load_json(HERE / 'owning-closure.json'))
    files.update(load_json(HERE / 'caller-inputs.json'))
    files.update(selected)
    files.update(b['installed_bytes'])
    prepared = {}
    for name in files:
        if name in b['new_paths']:
            continue
        raw = (read(HERE / b['predecessor_bytes'][name]['preimage'])
               if name in b['predecessor_bytes'] else read(ROOT / name))
        prepared[name] = raw
    need(len(prepared) <= 2048 and sum(map(len, prepared.values())) <= 64 * 1024 * 1024,
         'Predecessor budget exceeded')
    out.mkdir(parents=True, mode=0o700)
    for name, raw in prepared.items():
        p = out / relative(name)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
    for name in (PREVIOUS, 'verification/plan-continuation-2026-11-07/source113-inspection-caller-r3',
                 'verification/envelope-rust-1991-default-ci-adoption'):
        (out / name / 'control-scratch').mkdir(exist_ok=True)
    return {'files': len(prepared), 'bytes': sum(map(len, prepared.values())),
            'source121': digest(previous), 'out': str(out)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('verify'); p.add_argument('--workflow-installed', action='store_true')
    p = sub.add_parser('prepare-predecessor'); p.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('run'); p.add_argument('--out', type=Path, required=True); p.add_argument('--rustc', required=True)
    a = parser.parse_args()
    if a.command == 'verify':
        print(json.dumps(verify(a.workflow_installed), sort_keys=True))
    elif a.command == 'prepare-predecessor':
        print(json.dumps(prepare_predecessor(a.out), sort_keys=True))
    else:
        b, _, previous = admit()
        legacy = legacy_view(b, previous)
        old, base = legacy.legacy_view(legacy.admit()[0], legacy.admit()[2])
        prior_verify = base.verify
        def both(installed=False):
            admit()
            return dict(prior_verify(installed), native_report_source126=digest(load_json(HERE/'current-source-inputs.json')))
        base.verify = both
        return old.run_fixture(base, a.out, a.rustc)
    return 0


if __name__ == '__main__':
    sys.exit(main())
