#!/usr/bin/env python3
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time

HERE = Path(__file__).absolute().parent

def main():
    path = HERE / 'candidate-copy/check_cache_state.py'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == 'd30871f94721fff10a3b508670cc9520fc021812b1d39c4655a17420308635a7'
    spec = importlib.util.spec_from_file_location('corrected_candidate_traversal', path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    base = HERE / 'evidence/temporary-traversal'
    base.mkdir(parents=True, exist_ok=False)
    out = base / 'out'; out.mkdir()
    scratch = out / 'scratch'; scratch.mkdir()
    foreign = out / 'outside'; foreign.mkdir()
    receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
               'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'runner_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'commands': []}
    command = runner.Commands(out, receipt, time.monotonic() + 30)
    command.bind_scratch(scratch)
    traversal = scratch / '..' / 'outside'
    env = dict.fromkeys(['TMPDIR', 'TMP', 'TEMP'], str(traversal))
    code = 'import json,os,pathlib; p=pathlib.Path(os.environ["TMPDIR"])/"child-marker";p.write_bytes(b"outside-bound-scratch");print(json.dumps({"TMPDIR":os.environ["TMPDIR"],"actual_file":str(p.resolve())}))'
    text, _, child = command.run('temporary-traversal-actual-child', [sys.executable, '-B', '-c', code], out, env)
    observed = json.loads(text)
    assert child['exit'] == 0 and child['child_returned'] and child['owned_group_gone']
    assert Path(observed['actual_file']) == foreign / 'child-marker'
    assert not Path(observed['actual_file']).is_relative_to(scratch)
    marker_hash = hashlib.sha256((foreign / 'child-marker').read_bytes()).hexdigest()
    binding = base / 'binding-out'; binding.mkdir()
    other = runner.Commands(binding, {'commands': []}, time.monotonic() + 30)
    other.bind_scratch(binding / '..')
    assert other.scratch.resolve() == base and not other.scratch.resolve().is_relative_to(binding)
    receipt.update(normal_qualification_started=False, foreign_temporary_override_accepted=True,
        observed_child=observed, outside_marker_sha256=marker_hash,
        parent_traversal_scratch_binding_accepted=True,
        binding_requested=str(binding / '..'), binding_actual=str(other.scratch.resolve()),
        repair='Reject noncanonical parent traversal before bind_scratch and child_environment containment checks; test no-child rejection for both paths',
        source_or_pack_modified=False)
    shutil.rmtree(scratch); shutil.rmtree(foreign); shutil.rmtree(binding); shutil.rmtree(base / 'command-tmp')
    receipt['disposable_directories_removed'] = True
    receipt['children_reaped'] = True
    command.save()
    (base / 'finding.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print('CONFIRMED same TMP repair incomplete: actual traversal child wrote outside bound scratch; parent-traversal binding also accepted')

if __name__ == '__main__':
    main()
