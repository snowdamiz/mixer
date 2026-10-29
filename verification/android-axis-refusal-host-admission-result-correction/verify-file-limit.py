#!/usr/bin/env python3
"""Data-only inherited RLIMIT_FSIZE readback; no resource mutation or child launch."""
import json
import os
from pathlib import Path
import resource
import sys

output = Path(os.environ['MIXER_AXIS_OUT'])
prefix = os.environ.get('MIXER_AXIS_LIMIT_PREFIX', '')
assert prefix in ('', 'apple-'), 'Unexpected phase prefix'
blocks = int((output / (prefix + 'bash-file-limit-blocks.txt')).read_text().strip())
soft, hard = resource.getrlimit(resource.RLIMIT_FSIZE)
record = {'schema': 1, 'soft_bytes': soft, 'hard_bytes': hard,
          'bash_blocks': blocks, 'bash_version': os.environ['MIXER_AXIS_BASH_VERSION'],
          'python_version': sys.version, 'operation': 'resource.getrlimit(RLIMIT_FSIZE)'}
(output / (prefix + 'file-limit.json')).write_text(json.dumps(record, indent=2) + '\n')
assert blocks == 65536 and soft == hard == 67108864, 'Unexpected Bash/POSIX file-limit units'
