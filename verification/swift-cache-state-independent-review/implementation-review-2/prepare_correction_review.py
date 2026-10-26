"""Snapshot exact correction and mechanically rebind prior private review tooling."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = HERE.parent / 'implementation-review-1'
PUB_PATH = ROOT / 'verification/swift-semantic-adapter-root-review/guard-correction-public-review-admission.json'
PUB_SHA = '3230858dae7a43050c03f06c89202447f27627554302b6709df9c8f70b38f559'
PRIV_PATH = ROOT / 'verification/swift-semantic-adapter-root-review/guard-correction-private-review-admission.json'
PRIV_SHA = '5f7c86575d45090dd73fb42b6312335ce6123f17c3ddd1c98b9e49a071f628cb'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def checked(path, digest):
    raw = path.read_bytes()
    assert sha(raw) == digest, str(path)
    return raw


def main():
    public = json.loads(checked(PUB_PATH, PUB_SHA))
    private = json.loads(checked(PRIV_PATH, PRIV_SHA))
    for name, path, digest in [('root-public-admission.json', PUB_PATH, PUB_SHA), ('root-private-admission.json', PRIV_PATH, PRIV_SHA)]:
        (HERE / name).write_bytes(checked(path, digest))
    checked(OLD / 'review-seal.json', public['prior_review_seal_sha256'])
    for m in json.loads((OLD / 'review-seal.json').read_bytes())['members']:
        raw = (ROOT / m['path']).read_bytes()
        assert len(raw) == m['bytes'] and sha(raw) == m['sha256']
    seal_raw = checked(ROOT / public['candidate_seal'], public['candidate_seal_sha256'])
    seal = json.loads(seal_raw)
    target = HERE / 'candidate-snapshot'
    assert not target.exists(), 'preserve existing evidence'
    for m in seal['members']:
        raw = (ROOT / m['path']).read_bytes()
        assert len(raw) == m['bytes'] and sha(raw) == m['sha256']
        dest = target / m['path']
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
    write(HERE / 'candidate-snapshot-manifest.json', {'schema': 1,
        'at': datetime.now(timezone.utc).isoformat(), 'command': sys.argv,
        'python': sys.version, 'script_sha256': sha(Path(__file__).read_bytes()),
        'candidate_seal_sha256': public['candidate_seal_sha256'],
        'member_count': len(seal['members']), 'member_bytes': sum(m['bytes'] for m in seal['members']),
        'members': seal['members'],
        'access_order': 'Unchanged public runner verified all814/staged exact3 source first. This full snapshot precedes substantive corrected shape_q source review.',
        'producer_models_harness_tests_imported_or_executed': False})
    sources = {Path(m).name: target / m for m in public['source_members']}
    old_base = OLD / 'candidate-snapshot/verification/swift-cache-state-implementation/source/library'
    for name in ['analyzer.rs', 'envelope.rs']:
        assert (old_base / name).read_bytes() == sources[name].read_bytes()
    old = (old_base / 'cache_state.rs').read_text()
    new = sources['cache_state.rs'].read_text()
    begin = old.index('fn shape_q(')
    old_end = old.index('// Eligibility uses index MAX')
    new_begin = new.index('fn shape_q(')
    new_end = new.index('// Eligibility uses index MAX')
    assert old[:begin] == new[:new_begin] and old[old_end:] == new[new_end:]
    diff = ''.join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True), fromfile='original/cache_state.rs', tofile='correction-1/cache_state.rs'))
    (HERE / 'independent-production.diff').write_text(diff)
    write(HERE / 'source-diff-review.json', {'schema': 1, 'unchanged_libraries': ['analyzer.rs', 'envelope.rs'],
        'cache_state_original_sha256': sha(old.encode()), 'cache_state_corrected_sha256': sha(new.encode()),
        'only_changed_function': 'shape_q', 'unchanged_prefix_sha256': sha(old[:begin].encode()),
        'unchanged_suffix_sha256': sha(old[old_end:].encode()), 'production_diff_sha256': sha(diff.encode()),
        'source_accounting_and_lifetime_accepted': False,
        'source_reasoning': 'Masks are now checked only inside planned6..10. Stage7/8 now requires q15==1 before accepting pending in-range/selected. All prior source/accounting proof gaps remain pending.'})
    original_runner = (OLD / 'run_private_guards.py').read_text()
    text = original_runner
    replacements = [
        ('private-guard-review-admission.json', 'guard-correction-private-review-admission.json'),
        ('d52cb249fff84ed893e0f919cefff9095288a725ada60fa06db64743e893a586', PRIV_SHA),
        ("baseline = HERE / 'candidate-snapshot/verification/swift-cache-state-implementation/source/library'", "baseline = HERE / 'candidate-snapshot/verification/swift-cache-state-implementation/correction-1/source/library'"),
        ("product = ROOT / 'verification/swift-cache-state-implementation/source/library'", "product = ROOT / 'verification/swift-cache-state-implementation/correction-1/source/library'"),
        ("        source_receipt = []", "        public_path = ROOT / 'verification/swift-semantic-adapter-root-review/guard-correction-public-review-admission.json'\n        public = json.loads(checked(public_path, '" + PUB_SHA + "'))\n        require(a['public_admission_sha256'] == '" + PUB_SHA + "' and a['candidate_seal_sha256'] == public['candidate_seal_sha256'], 'exact corrected rebind')\n        corrected_seal = json.loads(checked(ROOT / public['candidate_seal'], public['candidate_seal_sha256']))\n        members = {m['path']: m for m in corrected_seal['members']}\n        baseline_hashes = {Path(p).name: members[p]['sha256'] for p in public['source_members']}\n        require(set(baseline_hashes) == {'analyzer.rs', 'envelope.rs', 'cache_state.rs'}, 'corrected three-source closure')\n        source_receipt = []"),
        ("for name, digest in delta['baseline_sha256'].items():", "for name, digest in baseline_hashes.items():"),
        ("result['product_baseline_hashes_unchanged_after'] = delta['baseline_sha256']", "result['product_baseline_hashes_unchanged_after'] = baseline_hashes")]
    for before, after in replacements:
        assert text.count(before) == 1, before
        text = text.replace(before, after)
    assert text.count("delta['baseline_sha256'][name]") == 2
    text = text.replace("delta['baseline_sha256'][name]", "baseline_hashes[name]")
    (HERE / 'run_private_guards.py').write_text(text)
    tooling_diff = ''.join(difflib.unified_diff(original_runner.splitlines(keepends=True), text.splitlines(keepends=True), fromfile='sealed-review-1/run_private_guards.py', tofile='review-2/run_private_guards.py'))
    (HERE / 'private-runner-rebind.diff').write_text(tooling_diff)
    write(HERE / 'private-runner-rebind.json', {'schema': 1, 'old_runner_sha256': sha(original_runner.encode()),
        'new_runner_sha256': sha(text.encode()), 'rebind_diff_sha256': sha(tooling_diff.encode()),
        'root_private_admission_sha256': PRIV_SHA, 'root_public_admission_sha256': PUB_SHA,
        'delta_unchanged': True, 'seven_full32_expectations_and_glue_unchanged': True,
        'scope': 'Mechanical admission/output/candidate-baseline rebind only; original delta baseline hashes remain historical and corrected exact hashes come from root admission/candidate seal.'})
    summary = json.loads((HERE / 'public-summary.json').read_bytes())
    api = json.loads((HERE / 'api-compile-summary.json').read_bytes())
    assert summary['count'] == 39 and summary['failures'] == 0
    assert len(api['controls']) == 15 and all(p['expected_disposition_and_attribution'] for p in api['controls'])
    print(json.dumps({'public_cases_passed': 39, 'expected_API_dispositions': 15, 'snapshot_members': len(seal['members']), 'private_runner_ready': True}))


if __name__ == '__main__':
    main()
