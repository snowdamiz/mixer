"""One-shot root selection of exact emitted-library evidence, not native support."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
def sha(b): return hashlib.sha256(b).hexdigest()
packets = []
for stem, expected in [
    ('android-api28-collections-prerequisite', '168ade73aa770bf1d3c6c595b3c24b55f3ed99dcba400d4422694b60c6749c0c'),
    ('android-api28-collections-independent', '1fd767e2fc14f13d7ee104c391e656afa94c6bbbb3855f818527e0aca3e37f8f'),
]:
    p = ROOT / 'verification' / stem / 'manifest.json'
    b = p.read_bytes(); assert sha(b) == expected
    d = json.loads(b); total = 0
    for name, row in d['files'].items():
        path = Path(name)
        assert not path.is_absolute() and '..' not in path.parts
        f = ROOT / path; assert not f.is_symlink()
        data = f.read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256'], name
        total += len(data)
    assert len(d['files']) == d['members'] and total == d['bytes']
    packets.append({'manifest': str(p.relative_to(ROOT)), 'sha256': expected,
                    'members_verified': len(d['files']), 'bytes': total})
producer = ROOT / 'verification/android-api28-collections-prerequisite'
review = ROOT / 'verification/android-api28-collections-independent'
sources = json.loads((producer / 'source-map.json').read_bytes())
java = {p:r for p,r in sources.items() if p.endswith('.java') and p.startswith('native/')}
assert len(java) == 20
for path, row in java.items():
    b = (ROOT / path).read_bytes()
    assert len(b) == row['bytes'] and sha(b) == row['sha256']
    assert b == (ROOT / row['snapshot']).read_bytes()
r = json.loads((review / 'receipt.json').read_bytes())
f = json.loads((review / 'final-receipt.json').read_bytes())
assert r['checks_count'] == len(r['checks']) == 851
assert len(r['commands']) == 8
assert all(c['exit_code'] == 0 and not c['timed_out'] and c['owned_child_reaped'] for c in r['commands'])
assert f['all23_profile4_snapshot_members_bound'] and f['fresh_exact_consumer_D8_byte_match']
assert f['owned_scratch_removed'] and f['fresh_negative_controls'] == 7
dex = (producer / 'consumer-flags/classes.dex').read_bytes()
result = {
    'schema': 1, 'at': datetime.datetime.now(datetime.UTC).isoformat(), 'python': sys.version,
    'command': 'python3 -B verification/android-api28-collections-root-review/accept.py',
    'context_revision': subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT).decode().strip(),
    'packets': packets, 'current_Java_sources_verified': 20,
    'exact_consumer_DEX_sha256': sha(dex), 'exact_consumer_DEX_bytes': len(dex),
    'decision': 'Accept exact emitted Java-library API floor and existing private read-only consumers; no source rewrite selected',
    'Java_member_ids': 170, 'Java_component_types': 60, 'decoded_code_bodies': 2307,
    'lowering_edges': 57, 'empty_edges': 15, 'independent_checks': 851,
    'independent_negative_controls': 7, 'independent_pure_source_JVM_assertions': 57,
    'separate_JDK_empty_mutator_mismatch_assertions': 8,
    'producer_prototype_not_selected_or_counted_as_independent': True,
    'independent_Group_records_three_writes_including_rollback_reviewed': True,
    'new_source_profile_or_product_rewrite_selected': False,
    'new_rendering_contexts': 0, 'both_API36_guards_unchanged': True,
    'universal_factory_mutation_exception_equivalence': False,
    'native_runtime_or_public_V2_or_OTA_or_GA_qualified': False,
    'limits': [
        'Exact source20, pinned official D8/SDK/JDK and compiler flags only; changed inputs require fresh emitted audit.',
        'Host source behavior and binary DEX inspection do not execute D8 helpers or establish Android verifier/class-loading/runtime behavior.',
        'Empty collection no-op mutator exceptions, hostile/concurrent collections, implementation identity, exception text and future callers are excluded.',
        'Builder has no automatic emitted API-floor gate; local tool lock is not a global approved binary allowlist. Tests cleared JVM option injection variables; equivalent compiler reproduction assumes these do not alter compilation.',
        'Framework/editor/insets/accessibility-value/visual accessibility support, public routing, TalkBack/parity/final phones, immutable published FieldLog, signing/store/operations/accountable GA remain pending.'
    ],
    'cleanup': 'Eight independent host children reaped and scratch removed; no native/capture process started'
}
with (OUT / 'acceptance.json').open('x') as o: json.dump(result,o,indent=2); o.write('\n')
print(json.dumps({'status':'accepted-exact-source-compiler-scope','members_verified':sum(p['members_verified'] for p in packets),'acceptance_sha256':sha((OUT/'acceptance.json').read_bytes())}))
