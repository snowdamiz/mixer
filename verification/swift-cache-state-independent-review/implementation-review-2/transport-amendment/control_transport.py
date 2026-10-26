"""Reviewer-owned lossless transport/integrity controls; zero candidate execution."""
from datetime import datetime, timezone
import copy
import json
from pathlib import Path
import sys
from dedup_transport import HERE, ROOT, PREP, build_pack, validate_pack, object_path, canonical, sealed
from harness import sha, write_json
import dedup_runner

OUT = HERE / 'controls'
checks = 0
rejections = []


def check(value, label):
    global checks
    checks += 1
    if not value:
        raise RuntimeError(label)


def refuses(label, call):
    global checks
    checks += 1
    try:
        call()
    except ValueError as exc:
        rejections.append({'id': label, 'type': type(exc).__name__, 'message': str(exc)})
        return
    raise RuntimeError('negative control unexpectedly accepted: ' + label)


def manifest_mutation(pack, label, change):
    path = pack / 'transport.json'
    before = path.read_bytes()
    value = json.loads(before)
    change(value)
    bad = canonical(value)
    (OUT / 'negative-evidence' / (label + '.json')).write_bytes(bad)
    try:
        path.write_bytes(bad)
        refuses(label, lambda: validate_pack(pack))
    finally:
        path.write_bytes(before)
    check(path.read_bytes() == before, label + ' exact restoration')


def main():
    if OUT.exists():
        raise ValueError('preserve prior controls')
    OUT.mkdir()
    (OUT / 'negative-evidence').mkdir()
    failure = None
    packs = []
    try:
        sealed.verify_preparation_and_preaccess({'reviewer_preparation_sha256': '07ff2daf1527fa459f68a4056b749ef71282b98f5b5a4ea634ba9ef19dae5ad6'})
        check(True, 'immutable reviewer tooling/preaccess fully verified')
        for kind, count in [('words', 64), ('transitions', 4), ('sequences', 4), ('basics', 2), ('terminal-full32', 64)]:
            path = OUT / (kind + '-pack')
            data = build_pack(kind, 0, count, path)
            readback = validate_pack(path)
            check(readback == data, kind + ' lossless manifest roundtrip')
            check(len(data['cases']) == count, kind + ' exact selected count')
            profiles = [v for v in data['objects'].values() if v['role'] == 'profile']
            if kind != 'terminal-full32':
                check(len(profiles) == 1, kind + ' one profile object per batch')
                for c in data['cases']:
                    check(len(c['expected_words']) == 32, kind + ' unchanged complete expected words')
            else:
                check(all(c['input_refs'] is None for c in data['cases']), 'private terminal has no public File payload')
                check(all('private' in c['coverage_layer'] for c in data['cases']), 'private terminal data never classified public')
            packs.append({'kind': kind, 'count': count, 'path': str(path.relative_to(HERE)),
                          'logical_input_bytes': data['logical_input_bytes'],
                          'unique_input_bytes': data['unique_input_bytes'],
                          'transport_sha256': sha((path / 'transport.json').read_bytes())})
        for kind, start, count in [('words', 0, 0), ('words', 0, 65), ('words', -1, 1), ('unknown', 0, 1), ('sequences', 251, 1)]:
            refuses('bounded-selection-' + kind + '-' + str(start) + '-' + str(count), lambda k=kind, s=start, c=count: build_pack(k, s, c, OUT / 'must-not-exist'))
            check(not (OUT / 'must-not-exist').exists(), 'rejection before output creation')
        words = OUT / 'words-pack'
        data = validate_pack(words)
        check(data['logical_input_bytes'] > data['unique_input_bytes'] * 32, '64-case payload storage reduced without byte loss')
        manifest_mutation(words, 'changed-expected-word', lambda d: d['cases'][0]['expected_words'].__setitem__(0, 99))
        def remap(d):
            other = next(c for c in d['cases'][1:] if c['input_refs']['stream'] != d['cases'][0]['input_refs']['stream'])
            d['cases'][0]['input_refs']['stream'] = other['input_refs']['stream']
        manifest_mutation(words, 'wrong-logical-stream-reference', remap)
        manifest_mutation(words, 'changed-source-case-reference', lambda d: d['cases'][0].__setitem__('source_item', d['cases'][1]['source_item']))
        def bad_path(d):
            d['objects'][d['cases'][0]['input_refs']['profile']]['path'] = '../outside'
        manifest_mutation(words, 'path-escape', bad_path)
        manifest_mutation(words, 'false-logical-byte-accounting', lambda d: d.__setitem__('logical_input_bytes', 1))
        profile = object_path(words, data, data['cases'][0]['input_refs']['profile'], 'profile')
        raw = profile.read_bytes()
        bad = raw[:-1] + bytes([raw[-1] ^ 1])
        write_json(OUT / 'negative-evidence/profile-byte-flip.json', {'base_sha256': sha(raw), 'bytes': len(raw),
            'offset': len(raw) - 1, 'old_byte': raw[-1], 'new_byte': bad[-1], 'mutated_sha256': sha(bad),
            'reconstruction': 'exact base object except one explicit byte replacement; raw base retained'})
        try:
            profile.write_bytes(bad)
            refuses('changed-profile-byte', lambda: validate_pack(words))
        finally:
            profile.write_bytes(raw)
        check(profile.read_bytes() == raw, 'changed profile exact restoration')
        backup = profile.with_suffix('.backup')
        try:
            profile.rename(backup)
            profile.symlink_to(backup.name)
            refuses('symlink-profile', lambda: validate_pack(words))
        finally:
            if profile.is_symlink():
                profile.unlink()
            if backup.exists():
                backup.rename(profile)
        check(profile.read_bytes() == raw and not profile.is_symlink(), 'symlink control exact restoration')
        manifest_mutation(OUT / 'terminal-full32-pack', 'terminal-misclassified-public', lambda d: d['cases'][0].__setitem__('input_refs', {}))
        refuses('no-new-root-transport-admission', lambda: dedup_runner.admission(
            'verification/swift-semantic-adapter-root-review/guard-correction-public-review-admission.json',
            '3230858dae7a43050c03f06c89202447f27627554302b6709df9c8f70b38f559', '0' * 64, 'words', 0, 64))
        for p in packs:
            validate_pack(HERE / p['path'])
        check(True, 'all retained pack bytes and manifests restored and revalidated')
    except Exception as exc:
        failure = {'type': type(exc).__name__, 'message': str(exc)}
    summary = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'python': sys.version,
        'script_sha256': sha(Path(__file__).read_bytes()), 'command': sys.argv,
        'checks': checks, 'intentional_refusals': rejections, 'packs': packs, 'failure': failure,
        'candidate_Rust_executions': 0, 'product_semantic_tests': 0,
        'producer_models_harness_tests_imported_or_executed': False,
        'scope': 'Reviewer-owned lossless encoding, hash/mapping, refusal and data-classification controls only',
        'cleanup': 'All owned negative mutations restored; sole owned process spawns no children; no compiler, runtime, native or process discovery',
        'source_hashes': {p.name: sha(p.read_bytes()) for p in [HERE / 'dedup_transport.py', HERE / 'dedup_runner.py', Path(__file__), PREP / 'future_runner.py', PREP / 'harness.py']}}
    write_json(OUT / 'summary.json', summary)
    print(json.dumps({'checks': checks, 'intentional_refusals': len(rejections), 'failure': failure, 'candidate_executions': 0}))
    return 0 if failure is None else 1


if __name__ == '__main__':
    raise SystemExit(main())
