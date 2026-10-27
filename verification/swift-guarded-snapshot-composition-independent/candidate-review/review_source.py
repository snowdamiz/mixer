"""Static source/custody supplements to the fresh compiler controls."""
import hashlib
import json
import pathlib
import re

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[2]
FROZEN = ROOT / 'verification/swift-guarded-snapshot-encoder-implementation/source/vm'
CANDIDATE = ROOT / 'verification/swift-guarded-snapshot-composition-source-preparation'
SOURCE = CANDIDATE / 'source/vm'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def block(text, prefix):
    begin = text.index(prefix)
    opening = text.index('{', begin)
    depth = 1
    for i in range(opening + 1, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}': depth -= 1
        if depth == 0: return text[begin:i+1]
    raise ValueError(prefix)


def main():
    checks = []
    def check(name, passed, detail):
        checks.append({'name': name, 'passed': passed, 'detail': detail})
        assert passed, (name, detail)
    initial_path = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
    initial = (SOURCE / initial_path).read_text()
    old_initial = (FROZEN / initial_path).read_text()
    for declaration in ['enum InitialProfileConstructionOutcomeV1', 'pub(crate) struct InitialProfileBorrowV1']:
        before, after = block(old_initial, declaration), block(initial, declaration)
        check('original declaration exact: ' + declaration, before == after, sha(after.encode()))
    for member in ['header.rs', 'selected.rs']:
        relative = 'src/experimental_swift_reactor/cache/initial_profile_v1/' + member
        before, after = (FROZEN / relative).read_bytes(), (SOURCE / relative).read_bytes()
        check('exact original ' + member, before == after, sha(after))
    for name in ['fn write_initial_profile_rows_v1', 'fn compare_budget_v1', 'fn inspect_initial_v1']:
        before, after = block(old_initial, name), block(initial, name)
        check('exact original ' + name, before == after, sha(after.encode()))
    control_path = 'src/experimental_swift_reactor/control.rs'
    control, old_control = (SOURCE / control_path).read_text(), (FROZEN / control_path).read_text()
    for name in ['pub(crate) struct RuntimeControl', 'pub(crate) fn end_construction_phase_with_wasi', 'pub(crate) fn finish_owned_cleanup', 'pub(crate) fn foundation_construction_bytes']:
        before, after = block(old_control, name), block(control, name)
        check('exact original ' + name, before == after, sha(after.encode()))
    encoder, old_encoder = (SOURCE / 'src/experimental/swift.rs').read_bytes(), (FROZEN / 'src/experimental/swift.rs').read_bytes()
    seam = b'\n' + (CANDIDATE / 'implementation/encoder_measurement.rs').read_bytes()
    assert encoder.count(seam) == 1
    recovered = encoder.replace(seam, b'', 1)
    check('exact encoder plus declared shape bridge', recovered == old_encoder + b'\n' + (CANDIDATE / 'implementation/shape.rs').read_bytes(),
          {'encoder_sha256': sha(old_encoder), 'shape_bridge_sha256': sha((CANDIDATE / 'implementation/shape.rs').read_bytes())})
    sources = [p for p in sorted(SOURCE.rglob('*')) if p.is_file()]
    changed = [str(p.relative_to(SOURCE)) for p in sources if p.read_bytes() != (FROZEN / p.relative_to(SOURCE)).read_bytes()]
    check('six changed source members', len(changed) == 6, changed)
    check('one candidate guard literal', len(re.findall(r'let initial\s*=\s*InitialProfileBorrowV1\s*\{', '\n'.join(p.read_text() for p in sources if p.suffix == '.rs'))) == 1, 'one exact candidate literal; compiler witnesses are separate variants')
    check('ordinary constructor uses statically Original associated output',
          'OriginalBranchV1)' in block(initial, 'fn construct_with_initial_profile_v1') and 'type Output=InitialProfileConstructionOutcomeV1;' in initial,
          'selected outer cannot be projected through Original return type')
    check('candidate emission always refuses', 'Err(AError::WorkAuditPending)' in block(initial, 'fn proposed_emission_work_v1'), 'no admitted writer execution follows this exact candidate')
    writer = block(initial, 'fn write_snapshot_v1')
    check('finite native operation sites', writer.count('.metadata()') == 2 and writer.count('.stream_position()') == 1 and writer.count('output.write(requested)') == 1 and 'for attempt in 1..=32u32' in writer,
          {'metadata_sites': 2, 'stream_position_sites': 1, 'write_site': 1, 'maximum_attempts_per_block': 32, 'flush_sync_truncate_sites': 0})
    counts = [67108864, 512, 8192, 34, 79966, 8192, 4096, 4096, 4096]
    widths = [0, 3, 1, 5, 3, 4, 4, 4, 4]
    words = sum(n * w for n, w in zip(counts, widths))
    extent = 2560 + counts[0] + words * 8
    blocks = (extent + 4095) // 4096
    check('independent shape envelope fits u64', extent < 1 << 64 and blocks > 0,
          {'counts': counts, 'words': words, 'extent': extent, 'blocks': blocks, 'maximum_native_writes': blocks * 32,
           'scope': 'arithmetic outer envelope only; capacities may not be jointly reachable; no work debit or floor'})
    data = {'schema': 1, 'checks': checks, 'scope': 'static differential/custody controls plus source-derived shape arithmetic; never release authorization by syntax alone'}
    (OUT / 'source-checks.json').write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'passed': len(checks), 'changed_members': len(changed)}))


if __name__ == '__main__':
    main()
