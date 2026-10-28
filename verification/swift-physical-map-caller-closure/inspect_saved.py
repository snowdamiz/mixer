#!/usr/bin/env python3
"""Bounded offline saved-artifact inspection. Never invokes a compiler or runtime."""
import datetime, hashlib, json, pathlib, platform, re, signal, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
signal.alarm(55)
START = time.monotonic()
NOW = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
H = lambda b: hashlib.sha256(b).hexdigest()
def write(name, value):
    data = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    (OUT / name).write_bytes(data)
    return {'path': str((OUT / name).relative_to(ROOT)), 'bytes': len(data), 'sha256': H(data)}
def pin(path, data):
    st = path.stat()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': H(data),
            'device': st.st_dev, 'inode': st.st_ino, 'mtime_ns': st.st_mtime_ns}
def span(data, begin, end):
    return {'byte_begin': begin, 'byte_end_exclusive': end,
            'line_begin': data.count(b'\n', 0, begin) + 1,
            'line_end_inclusive': data.count(b'\n', 0, end - 1) + 1,
            'bytes': end-begin, 'sha256': H(data[begin:end])}

selection_path = ROOT/'verification/swift-semantic-adapter-root-review/dispatch-physical-mapping-selection.json'
selection_data = selection_path.read_bytes()
selection = json.loads(selection_data)
method = {
 'schema': 1, 'at': NOW(), 'status': 'frozen-before-raw-artifact-access',
 'owned_targets': ['Caller', 'Closure'], 'owned_directory': str(OUT.relative_to(ROOT)),
 'command': 'python3 verification/swift-physical-map-caller-closure/inspect_saved.py',
 'tool': {'python_implementation': platform.python_implementation(), 'python_version': sys.version,
          'version_provenance': 'running stdlib inspection process; no compiler/version subprocess'},
 'script': pin(pathlib.Path(__file__), pathlib.Path(__file__).read_bytes()),
 'source_revision': '9e860ea12074ca31bef4087ce34177a03f295dd8',
 'selection': pin(selection_path, selection_data),
 'input_bounds': selection['bounds'],
 'method': [
  'Read only the selected exact LLVM and assembly artifacts, validate size and whole SHA-256 before interpreting them.',
  'Index every LLVM define header to its standalone closing brace, rejecting unclosed or nested definitions. Match Caller/Closure by linkage and DISubprogram identity; mere mentions do not count.',
  'Index every LLVM debug metadata node and preserve the selected function debug/source/scope chain.',
  'Locate each selected assembly label with Mach-O leading underscore adjustment, then preserve complete .cfi_startproc through .cfi_endproc boundaries and whole hashes. Fail incomplete if any boundary or match is absent or ambiguous.',
  'Record every direct call/invoke operand and all assembly bl/blr instructions in each selected whole function, with exact original line/byte provenance.',
  'Hash pinned original source and MIR files and verify exact target spans, retaining bounded excerpts without silently truncating function evidence.',
  'Represent whole function evidence by exact spans and SHA-256 over retained original artifacts; optional excerpts explicitly state coverage and any omission.',
  'Rehash raw artifacts and pinned source/MIR after inspection and record equality. Preserve raw inputs.',
  'Do not invoke a compiler, native runtime, tests, model, geometry verifier, external version tool, or modify product/global metadata.'
 ],
 'interpretation_limits': ['mapping only', 'no physical geometry, alias, stack peak, capacity, backing, destruction, price, root funding, semantic approval, device, or GA acceptance'],
 'no_silent_truncation': True,
}
write('index-method.json', method)
raws = {}
before = []
for expected in selection['artifacts']:
    path = ROOT/expected['path']; data = path.read_bytes(); p = pin(path, data)
    assert (p['bytes'], p['sha256']) == (expected['bytes'], expected['sha256']), p
    raws[path.suffix] = (path, data)
    before.append(p)
assert sum(p['bytes'] for p in before) <= 64 * 1024 * 1024
write('input-pins-before.json', {'schema': 1, 'at': NOW(), 'raw_artifacts': before,
                               'total_distinct_raw_artifact_bytes': sum(p['bytes'] for p in before)})
ll_path, ll = raws['.ll']; asm_path, asm = raws['.s']
def offsets(data):
    pos = 0
    for line in data.splitlines(keepends=True):
        yield pos, line
        pos += len(line)

definitions = []
current = None
for off, line in offsets(ll):
    if line.startswith(b'define '):
        assert current is None, ('nested-definition', off)
        m = re.search(rb'@(?:"([^"\n]+)"|([^\s(]+))\(', line)
        assert m, ('unparsed-definition', off)
        current = (off, line, (m[1] or m[2]).decode())
    elif current and line.rstrip(b'\r\n') == b'}':
        begin, header, symbol = current
        definitions.append((begin, off + len(line), header, symbol))
        current = None
assert current is None, ('unclosed-definition', current)
selected = [d for d in definitions if 'run_one_admitted_fixture_v1' in d[3]]
mentions = []
for off, line in offsets(ll):
    if b'run_one_admitted_fixture_v1' in line:
        mentions.append({'span': span(ll, off, off+len(line)), 'text': line.decode()})
asm_mentions = []
for off, line in offsets(asm):
    if b'run_one_admitted_fixture_v1' in line:
        asm_mentions.append({'span': span(asm, off, off+len(line)), 'text': line.decode()})
candidate_records = []
for begin, end, header, symbol in selected:
    candidate_records.append({'symbol': symbol, 'span': span(ll, begin, end), 'header': header.decode()})
write('candidate-index.json', {'schema': 1, 'at': NOW(),
 'llvm_definition_count_all': len(definitions), 'llvm_candidate_definitions': candidate_records,
 'llvm_all_target_mentions': mentions, 'assembly_all_target_mentions': asm_mentions,
 'raw_artifacts': before, 'completeness': 'full raw artifacts indexed; all literal target mentions included; no function body claims yet'})
after = [pin(path, path.read_bytes()) for path, data in raws.values()]
assert after == before
write('input-pins-after-index.json', {'schema': 1, 'at': NOW(), 'raw_artifacts': after,
 'equal_before': after == before, 'elapsed_seconds': time.monotonic()-START,
 'derived_bytes': sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())})
assert sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()) <= 8*1024*1024
print(json.dumps({'selected_definitions': candidate_records, 'llvm_mentions': len(mentions),
                  'asm_mentions': len(asm_mentions), 'derived_bytes': sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()),
                  'elapsed_seconds': time.monotonic()-START}, indent=2))
