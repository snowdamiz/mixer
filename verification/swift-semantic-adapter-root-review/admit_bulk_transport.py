"""Admit three bounded independent public fixture batches; source proofs stay open."""
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(path, expected):
    assert sha(path) == expected
    d = json.loads(path.read_bytes())
    assert len({m['path'] for m in d['members']}) == d['member_count']
    for m in d['members']:
        name = PurePosixPath(m['path'])
        assert not name.is_absolute() and '..' not in name.parts
        p = ROOT
        for part in name.parts:
            p /= part
            assert not p.is_symlink()
        assert p.is_file() and p.stat().st_size == m['bytes'] and sha(p) == m['sha256']
    assert sum(m['bytes'] for m in d['members']) == d['member_bytes']
    return d
transport_path = ROOT / 'verification/swift-cache-state-independent-review/implementation-review-2/transport-amendment/transport-seal.json'
transport_sha = '27d8d6313c7578c8bb486d5044b68f1a1482945e338e7c111ec8635f04879afc'
t = verify(transport_path, transport_sha)
assert (t['member_count'], t['member_bytes']) == (252, 11264975)
base_path = OUT / 'guard-correction-public-review-admission.json'
assert sha(base_path) == '3230858dae7a43050c03f06c89202447f27627554302b6709df9c8f70b38f559'
base = json.loads(base_path.read_bytes())
c = verify(ROOT / base['candidate_seal'], base['candidate_seal_sha256'])
assert c['member_count'] == 814
assert sha(Path(base['rustc'])) == base['rustc_sha256']
admissions = []
for kind in ('words', 'transitions', 'sequences'):
    value = dict(base)
    value.update({
        'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': sys.argv, 'python': sys.version, 'script_sha256': sha(Path(__file__)),
        'dedup_transport': {'seal': transport_path.relative_to(ROOT).as_posix(), 'seal_sha256': transport_sha,
            'execution_authorized': True, 'verified_members': 252, 'verified_bytes': 11264975},
        'selected_case_set': kind, 'selected_start': 0, 'selected_count': 64,
        'review_output_directory': 'verification/swift-cache-state-independent-review/implementation-review-2/bulk-' + kind + '-0000-root',
        'scope': 'Exactly64 public four-File cases from the unchanged independent preaccess fixture set, through the lossless role/content transport and unchanged full32/report/input comparator. No additional API/private tests, no work-budget or lifetime acceptance.',
        'source_accounting_status': 'Conditional G6 blocker and remedy proposal under separate independent review. These executions cannot authorize source-budget or implementation acceptance.',
        'run_sequence': 'words then transitions then sequences; stop on first nonzero exit or case failure, preserve raw evidence without changing expectations.',
        'additional_batches_authorized': False,
    })
    p = OUT / ('bulk-' + kind + '-0000-admission.json')
    assert not p.exists()
    p.write_text(json.dumps(value, indent=2) + '\n')
    admissions.append({'kind': kind, 'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p)})
print(json.dumps(admissions))
