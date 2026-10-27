#!/usr/bin/env python3
"""Immutable data-only packet seal and read-only reproduction."""
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from prepare import HERE, sha, canonical, source_data

def snapshot():
    _, manifest, _, _ = source_data()
    assert not (HERE/'owned-work').exists(), 'owned compiler scratch must be removed'
    assert not list(HERE.rglob('__pycache__'))
    members = [dict(path=p.relative_to(HERE).as_posix(), bytes=len(p.read_bytes()),
                    sha256=sha(p.read_bytes()))
        for p in sorted(HERE.rglob('*')) if p.is_file() and p != HERE/'seal.json']
    return dict(schema=1, members=members, member_count=len(members),
        member_bytes=sum(m['bytes'] for m in members),
        manifest_sha256=sha(canonical(members)), source_members=146,
        candidate_source_tree_sha256=manifest['tree_sha256'],
        source_only_candidate=True, compiler_invocations=1,
        compiler_terminal_exit_status='unknown; original receipt-writer error preserved',
        compiler_terminal_success_claim=False,
        actual_fixture_or_product_runtime=False,
        root_policy_whole_quote_and_immutable_binding_pending=True,
        new_outer_work_storage_price_selected=False,
        independent_review=False, native_OTA_FieldLog_GA=False)

def main():
    data = (json.dumps(snapshot(), indent=2, sort_keys=True)+'\n').encode()
    if '--check-only' in sys.argv:
        assert (HERE/'seal.json').read_bytes() == data, 'frozen candidate changed'
    else:
        assert not (HERE/'seal.json').exists(), 'refuse to replace seal'
        (HERE/'seal.json').write_bytes(data)
    print(json.dumps(dict(passed=True, seal_sha256=sha(data),
        members=json.loads(data)['member_count'], member_bytes=json.loads(data)['member_bytes'],
        mode='check-only' if '--check-only' in sys.argv else 'freeze')))

if __name__ == '__main__': main()
