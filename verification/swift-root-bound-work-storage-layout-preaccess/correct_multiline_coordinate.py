#!/usr/bin/env python3
"""Preserve the first oracle; correct one coordinate before producer access."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def row(path):
    raw = path.read_bytes()
    return {'path': path.name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


bindings = json.loads((HERE / 'diagnostic-bindings.json').read_bytes())
query = bindings['closure_queries'][1]['expression']
old_column_end = query['column_end']
assert old_column_end == query['column_start'] + len(query['text'])
assert query['text'].count('\n') == 2
query['column_end'] = len(query['text'].rsplit('\n', 1)[1]) + 1
assert query['column_end'] == 15
with (HERE / 'diagnostic-bindings-corrected.json').open('x') as stream:
    json.dump(bindings, stream, indent=2, sort_keys=True)
    stream.write('\n')
correction = {
    'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'FROZEN_PREACCESS_COORDINATE_CORRECTION',
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(HERE.parents[1]))],
    'python': sys.version, 'script': row(Path(__file__)),
    'original_oracle': row(HERE / 'preaccess-oracle.json'),
    'original_bindings': row(HERE / 'diagnostic-bindings.json'),
    'corrected_bindings': row(HERE / 'diagnostic-bindings-corrected.json'),
    'correction': {'path': ['closure_queries', 1, 'expression', 'column_end'],
                   'old': old_column_end, 'new': query['column_end'],
                   'reason': 'Multiline span end column is the last line length plus one, not start column plus complete token length.'},
    'failure_attribution': 'Reviewer coordinate helper defect caught by positive synthetic parser control before new producer access; not a producer finding.',
    'failure_artifacts': [row(HERE / name) for name in ['parser-controls.stdout', 'parser-controls.stderr']],
    'source_bytes_tree_identity_or_query_strategy_changed': False,
    'new_producer_lane_accessed': False, 'compiler_or_runtime_executed': False,
    'diagnostic_strategy_qualified': False}
with (HERE / 'preaccess-oracle-correction.json').open('x') as stream:
    json.dump(correction, stream, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps({'correction': row(HERE / 'preaccess-oracle-correction.json'),
                  'corrected_bindings': correction['corrected_bindings'],
                  'new_producer_lane_accessed': False}))
