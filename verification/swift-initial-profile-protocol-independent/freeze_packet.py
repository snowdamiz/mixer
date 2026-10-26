#!/usr/bin/env python3
"""Freeze only this independently owned review folder after finite checks."""
from pathlib import Path
import datetime
import hashlib
import json

OUT = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(name):
    return json.loads((OUT / name).read_text())

def main():
    decision = read('decision.json')
    assert not decision['contract_blockers']
    assert not decision['required_contract_amendments']
    assert decision['offline_checks']['final_status'] == 'passed'
    assert decision['offline_checks']['methods'] == 16
    for run in ['run001', 'run002']:
        receipt = read(f'commands/{run}/receipt.json')
        for stream in ['stdout', 'stderr']:
            assert sha(OUT / f'commands/{run}/{stream}') == receipt[f'{stream}_sha256']
        assert sha(OUT / f'commands/{run}/check_packet.py') == receipt['checker_sha256']
    assert read('commands/run001/receipt.json')['exit_code'] == 1
    final = read('commands/run002/receipt.json')
    assert final['exit_code'] == 0
    assert sha(OUT / 'check_packet.py') == final['checker_sha256']
    closure = read('future-closure.json')
    assert len(set(closure['distribution_paths'])) == 140
    assert len(set(closure['host_support_paths'])) == 11
    assert all(not p.is_symlink() for p in OUT.rglob('*'))
    assert not list(OUT.rglob('__pycache__'))
    members = []
    for path in sorted((p for p in OUT.rglob('*') if p.is_file()),
                       key=lambda p: p.relative_to(OUT).as_posix()):
        relative = path.relative_to(OUT).as_posix()
        if relative in ['seal.json', 'seal.sha256']:
            continue
        members.append(dict(path=relative, bytes=path.stat().st_size, sha256=sha(path)))
    material = ''.join(f"{m['path']}\t{m['bytes']}\t{m['sha256']}\n" for m in members).encode()
    seal = dict(schema=1, at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Independent frozen contract and data/custody review only; no product/lifetime/accounting/runtime acceptance',
        excluded=['seal.json', 'seal.sha256'], member_count=len(members),
        total_bytes=sum(m['bytes'] for m in members), members=members,
        tree_definition='SHA256 sorted full relative string path TAB decimal bytes TAB lowercase sha256 LF',
        tree_sha256=hashlib.sha256(material).hexdigest(),
        product_implementation_or_actual_guard_lifetime_or_combined_accounting_or_runtime_or_GA_accepted=False)
    (OUT / 'seal.json').write_text(json.dumps(seal, indent=2, sort_keys=True) + '\n')
    seal_sha = sha(OUT / 'seal.json')
    (OUT / 'seal.sha256').write_text(seal_sha + '  seal.json\n')
    print(json.dumps(dict(seal_sha256=seal_sha, member_count=seal['member_count'],
        total_bytes=seal['total_bytes'], tree_sha256=seal['tree_sha256'])))

if __name__ == '__main__':
    main()
