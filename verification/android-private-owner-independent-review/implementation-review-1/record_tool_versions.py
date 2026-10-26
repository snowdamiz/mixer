#!/usr/bin/env python3
"""Record exact local official host tools through the owned bounded child runner."""
from pathlib import Path
import hashlib
import json
import sys
import run_targeted_review as runner

HERE = Path(__file__).resolve().parent


def main():
    out = HERE / 'tools'
    out.mkdir(exist_ok=True)
    source = {'record_tool_versions.py':runner.record(Path(__file__)),
              'run_targeted_review.py':runner.record(HERE / 'run_targeted_review.py')}
    for tool in ['javac', 'java', 'javap']:
        result = runner.run([str(runner.JDK / tool), '-version'], out / tool, source)
        assert result['exit_code'] == 0
    executable = Path(sys.executable).resolve()
    (out / 'python.json').write_text(json.dumps(dict(version=sys.version, executable=str(executable),
        executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
        scope='Recording/orchestration interpreter; no producer runner imported'), indent=2) + '\n')


if __name__ == '__main__':
    main()
