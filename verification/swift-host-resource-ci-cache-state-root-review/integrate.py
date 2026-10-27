"""One-shot integration of the reviewed context-fixture setup correction."""
from pathlib import Path
import datetime
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CI = ROOT / 'verification/swift-cache-state-ci'
PACK = CI / 'pack'
REPAIR = ROOT / 'verification/swift-host-resource-ci-cache-state-repair'
sha = lambda b: hashlib.sha256(b).hexdigest()
encode = lambda v: (json.dumps(v, sort_keys=True, indent=2) + '\n').encode()

def main():
    assert not (OUT / 'integration.json').exists(), 'One-shot integration'
    member = PACK / 'source/regression/independent_tests.rs'
    original = member.read_bytes()
    assert sha(original) == '140833c2d18655b77769d3f4c1346aee4b0f43aed25dae8e7160860adcd5033f'
    proposed = (REPAIR / 'proposal/independent_tests.rs').read_bytes()
    assert sha(proposed) == '7c9c3006e1e7fd6a927fc7c3ca472c33abe3084f50a1f5aea0d31c6d9d75c411'
    start = original.index(b'fn context_schema_scalar_reserved_and_lengths() {')
    end = original.index(b'\n#[test]', start)
    body = original[start:end]
    assert body.count(b'Fixture::new()') == 3
    expected = body.replace(b'Fixture::new()', b'baseline.clone()').replace(b'() {\n', b'() {\n    let baseline=Fixture::new();\n', 1)
    assert proposed == original[:start] + expected + original[end:]
    focused = json.loads((REPAIR / 'runs/focused-2/receipt.json').read_bytes())
    assert focused['status'] == 'passed-focused-fixture-proposal' and focused['errors'] == []
    assert focused['exact_proposal']['focused_context_cases'] == 1003
    assert focused['independent_equivalence']['exact_stream_profile_context_bytes'] is True
    assert focused['independent_equivalence']['per_case_cleanups'] == 1003
    assert focused['cleanup']['removed'] and focused['cleanup']['groups_returned']
    paths = [member, PACK / 'inventories/source-roster.json', PACK / 'inventories/bindings.json', PACK / 'manifest.json', CI / 'check_cache_state.py']
    before = {str(p.relative_to(ROOT)): {'bytes': len(p.read_bytes()), 'sha256': sha(p.read_bytes())} for p in paths}
    preimages = OUT / 'preimages'
    preimages.mkdir()
    for path in paths:
        (preimages / path.name).write_bytes(path.read_bytes())
    old_manifest = json.loads((PACK / 'manifest.json').read_bytes())
    assert sha((PACK / 'manifest.json').read_bytes()) == '6c52eb0ed737530d92011ce63e1eda593159c670b262a5f7bcf8b54b5338d857'
    member.write_bytes(proposed)
    roster_path = PACK / 'inventories/source-roster.json'
    roster = json.loads(roster_path.read_bytes())
    selected = [r for r in roster['rows'] if r['packed'] == 'source/regression/independent_tests.rs']
    assert len(selected) == 1
    row = selected[0]
    row['historical_predecessor'] = dict(row)
    row['original'] = 'verification/swift-host-resource-ci-cache-state-repair/proposal/independent_tests.rs'
    row['sha256'], row['bytes'] = sha(proposed), len(proposed)
    row['amendment'] = 'One baseline plus independent clones in the context1003 fixture; exact inputs and original analyzer assertions preserved.'
    roster['selected_source_bytes'] = sum(r['bytes'] for r in roster['rows'])
    roster_path.write_bytes(encode(roster))
    bindings_path = PACK / 'inventories/bindings.json'
    bindings = json.loads(bindings_path.read_bytes())
    bindings['historical_source_tree_sha256'] = bindings.pop('source_tree_sha256')
    bindings['fixture_setup_amendment'] = {
        'original_source_sha256': sha(original), 'revised_source_sha256': sha(proposed),
        'focused_receipt': 'verification/swift-host-resource-ci-cache-state-repair/runs/focused-2/receipt.json',
        'focused_receipt_sha256': sha((REPAIR / 'runs/focused-2/receipt.json').read_bytes()),
        'case_count': 1003, 'library_sources_unchanged': True, 'method_inventory_unchanged': True,
        'full_qualification_required': True, 'original_CI_timeout_remains_failed': True,
    }
    bindings_path.write_bytes(encode(bindings))
    rows = []
    for p in sorted(PACK.rglob('*')):
        if p.is_file() and p.name != 'manifest.json':
            assert not p.is_symlink()
            data = p.read_bytes()
            rows.append({'path': p.relative_to(PACK).as_posix(), 'bytes': len(data), 'sha256': sha(data)})
    assert len(rows) == old_manifest['member_count'] == 86
    revised = dict(old_manifest)
    revised.update(members=rows, total_bytes=sum(r['bytes'] for r in rows), tree_sha256=sha(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()))
    revised['source_revision_scope'] = 'Accepted library/API closure with reviewed context1003 fixture-setup amendment; exact current members are pinned here. Each compiler requires fresh complete qualification.'
    (PACK / 'manifest.json').write_bytes(encode(revised))
    runner = CI / 'check_cache_state.py'
    raw = runner.read_bytes()
    old = b"MANIFEST_SHA256='6c52eb0ed737530d92011ce63e1eda593159c670b262a5f7bcf8b54b5338d857'"
    assert raw.count(old) == 1
    runner.write_bytes(raw.replace(old, b"MANIFEST_SHA256='" + sha((PACK / 'manifest.json').read_bytes()).encode() + b"'"))
    after = {str(p.relative_to(ROOT)): {'bytes': len(p.read_bytes()), 'sha256': sha(p.read_bytes())} for p in paths}
    result = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'reviewed-fixture-correction-integrated-complete-qualification-pending', 'before': before, 'after': after, 'changed_fixture_members': 1, 'case_count': 1003, 'library_changed': False, 'bounds_or_case_assertions_changed': False, 'source_roster_has_explicit_predecessor': True, 'old_pack_preimages_retained': True, 'new_manifest_sha256': sha((PACK / 'manifest.json').read_bytes()), 'new_pack_tree_sha256': revised['tree_sha256'], 'reviewer_preflight_failure': 'Initial preflight expected a generic passed status; the focused producer status is passed-focused-fixture-proposal. It failed before preimages or mutations; corrected to the exact scoped status.', 'native_runtime_or_GA': False}
    with (OUT / 'integration.json').open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
