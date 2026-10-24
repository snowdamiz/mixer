#!/usr/bin/env python3
"""Prepare only the selected SL13 ticket/cache-entry assertions from sealed V2."""
from pathlib import Path
import difflib, hashlib, json, shutil, subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'verification/swift-reactor-lifecycle-runtime-v2'
SELECTION = ROOT / 'verification/swift-reactor-lifecycle-runtime-v2-root-review/v3-ticket-test-repair-selection.json'
SELECTED = 'swift_lifecycle_sl13_cumulative_instruction_host_and_cache_usage'
FILE = 'src/experimental_swift_reactor/lifecycle_tests.rs'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
enc = lambda value: (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
def manifest(tree):
    return {str(p.relative_to(tree)): sha(p.read_bytes()) for p in sorted(tree.rglob('*')) if p.is_file()}
def bounds(text):
    start = text.index('fn ' + SELECTED + '(')
    opening = text.index('{', start)
    end, depth = opening + 1, 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return opening, end
def mask(text):
    start, end = bounds(text)
    return text[:start] + '{SELECTED_BODY}' + text[end:]

def main():
    assert sha(SELECTION.read_bytes()) == '27c2c8a4a134a5c1d3b4510487b4c67eb95a1cd75b36d9b688c0c5f320ac096e'
    assert sha((OLD / 'seal.json').read_bytes()) == '36d70c601ce2930ef18ca7adb58dcb96b4e3e3e15d816406c0b7df092e81d749'
    sealed = json.loads((OLD / 'seal.json').read_bytes())
    for name, pin in sealed['files'].items():
        assert sha((OLD / name).read_bytes()) == pin, name
    old = manifest(OLD / 'candidate')
    assert sha(enc(old)) == '0fa7ae254ac2b3aa3390e6fbc935e920422fc9024db220256074ec6ef4e3cd56'
    assert not (HERE / 'candidate').exists()
    shutil.copytree(OLD / 'candidate', HERE / 'candidate')
    path = HERE / 'candidate' / FILE
    before = path.read_text()
    start, end = bounds(before)
    body = before[start:end]
    edits = [
        ('    let start = observed(&o);\n',
         '    let start = observed(&o);\n    assert_eq!(start.live.cache_entries.current, 0);\n'),
        ('    let initialized = observed(&o);\n',
         '    let initialized = observed(&o);\n    // Resident Cache tickets belong to decoded entries, surviving pin release.\n    assert_eq!(initialized.reservations.live_tickets - start.reservations.live_tickets, 1);\n    assert_eq!(initialized.live.cache_entries.current, 1);\n'),
        ('    let first = observed(&o);\n',
         '    let first = observed(&o);\n    assert_eq!(first.reservations.live_tickets - initialized.reservations.live_tickets, 2);\n    assert_eq!(first.live.cache_entries.current, 3);\n'),
        ('    let second = observed(&o);\n',
         '    let second = observed(&o);\n    assert_eq!(second.reservations.live_tickets - first.reservations.live_tickets, 0);\n    assert_eq!(second.live.cache_entries.current, 3);\n'),
        ('    assert_eq!(\n        second.reservations.live_tickets,\n        initialized.reservations.live_tickets\n    );\n', ''),
    ]
    for old_text, new_text in edits:
        assert body.count(old_text) == 1, old_text
        body = body.replace(old_text, new_text, 1)
    after = before[:start] + body + before[end:]
    assert mask(before) == mask(after)
    # Preserve every pre-existing SL13 assertion except the one rejected by selection.
    removed = edits[-1][0]
    surviving = before[start:end].replace(removed, '')
    cursor = 0
    for line in surviving.splitlines(True):
        found = body.find(line, cursor)
        assert found >= 0, line
        cursor = found + len(line)
    path.write_text(after)
    formatted = subprocess.run(['/opt/homebrew/opt/rustup/bin/rustfmt', '--edition', '2021', str(path)], capture_output=True)
    (HERE / 'format.stdout').write_bytes(formatted.stdout)
    (HERE / 'format.stderr').write_bytes(formatted.stderr)
    assert formatted.returncode == 0
    after = path.read_text()
    assert mask(before) == mask(after), 'rustfmt changed unselected bytes'
    new = manifest(HERE / 'candidate')
    assert set(old) == set(new)
    assert [name for name in new if old[name] != new[name]] == [FILE]
    for name in ['authored-coverage.json', 'planned-matrix-unchanged.json']:
        (HERE / name).write_bytes((OLD / name).read_bytes())
    (HERE / 'test-repair-selection.json').write_bytes(SELECTION.read_bytes())
    (HERE / 'prior-seal.json').write_bytes((OLD / 'seal.json').read_bytes())
    (HERE / 'candidate-manifest.json').write_bytes(enc(new))
    (HERE / 'candidate.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='sealed-v2/' + FILE, tofile='candidate-v3/' + FILE)))
    delta = {'schema': 'mixer.swift-lifecycle.v3-source-delta.1', 'candidateClosure': sha(enc(new)), 'previousClosure': sha(enc(old)), 'priorSealSHA256': sha((OLD / 'seal.json').read_bytes()), 'selectionSHA256': sha(SELECTION.read_bytes()), 'changedFile': FILE, 'changedBodies': [SELECTED], 'unchangedFiles': len(new) - 1, 'allOtherFileAndHelperImportHookTestBytesExact': True, 'productionLifecycleGrowthAccountingAndFrozenSourceExact': True, 'retainedAllOtherSL13ChecksDeadlineAndConsumingRetire': True, 'additionalAccountingCredit': 0, 'runtimeExecuted': False}
    (HERE / 'source-delta.json').write_bytes(enc(delta))
    print(enc(delta).decode())

if __name__ == '__main__':
    main()
