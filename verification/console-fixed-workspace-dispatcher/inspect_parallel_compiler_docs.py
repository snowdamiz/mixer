#!/opt/homebrew/opt/python@3.14/bin/python3.14
"""Read pinned BEAM documentation bytes with Python only; never execute BEAM."""
from pathlib import Path
import hashlib
import json
import zlib

BEAM = Path('/opt/homebrew/Cellar/elixir/1.20.4/lib/elixir/lib/elixir/ebin/Elixir.Kernel.ParallelCompiler.beam')
data = BEAM.read_bytes()
position = 12
while position < len(data):
    name = data[position:position + 4]
    size = int.from_bytes(data[position + 4:position + 8], 'big')
    if name == b'Docs':
        docs = data[position + 8:position + 8 + size]
        break
    position += 8 + (size + 3) // 4 * 4
if docs[1] == 80:
    docs = bytes([131]) + zlib.decompress(docs[6:])
position = 1

def term():
    global position
    tag = docs[position]
    position += 1
    if tag == 97:
        value = docs[position]
        position += 1
        return value
    if tag == 98:
        value = int.from_bytes(docs[position:position + 4], 'big', signed=True)
        position += 4
        return value
    if tag in [100, 118, 107, 115, 119, 109]:
        width = 1 if tag in [115, 119] else 4 if tag == 109 else 2
        size = int.from_bytes(docs[position:position + width], 'big')
        position += width
        value = docs[position:position + size].decode('utf-8')
        position += size
        return value
    if tag in [104, 105, 108, 116]:
        width = 1 if tag == 104 else 4
        size = int.from_bytes(docs[position:position + width], 'big')
        position += width
        if tag == 116:
            return {str(term()): term() for _ in range(size)}
        values = [term() for _ in range(size)]
        if tag == 108:
            assert term() == []
        return values
    if tag == 106:
        return []
    raise ValueError('unsupported documentation term tag')

entries = term()[-1]
selected = []
for row in entries:
    if row[0][1] in ['compile', 'compile_to_path']:
        selected.append({'entry': row[0], 'documentation': row[3]['en'].split('## Options')[0]})
result = {'schema': 1, 'command': ['/opt/homebrew/opt/python@3.14/bin/python3.14', '-B', 'verification/console-fixed-workspace-dispatcher/inspect_parallel_compiler_docs.py'], 'tool': 'Python stdlib only; no Elixir/BEAM/compiler execution', 'source': str(BEAM), 'source_sha256': hashlib.sha256(data).hexdigest(), 'documentation': selected, 'decision': 'Use return_diagnostics:true and require exact zero compile_warnings/runtime_warnings lists. Report fixed count/classification for all other compiler results.'}
output = Path(__file__).with_name('parallel-compiler-diagnostics-docs.json')
output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
