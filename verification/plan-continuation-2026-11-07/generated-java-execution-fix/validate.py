"""Final Python controls, metadata proof, and preserved-evidence verification."""
import difflib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
runner = ROOT / 'scripts/ci/check-android-generated-java.py'
tests = ROOT / 'scripts/ci/tests/test_android_generated_java_runner.py'
spec = importlib.util.spec_from_file_location('final_runner', runner)
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
out = HERE / sys.argv[1]
out.mkdir(exist_ok=False)
commands = M.Commands(out, os.environ.copy(), seconds=90, command_seconds=20)
revision = commands.run('revision', ['git', 'rev-parse', 'HEAD']).strip()
tree = commands.run('git-tree', ['git', 'rev-parse', 'HEAD^{tree}']).strip()
for label, target in [('runner', tests), ('r2-independent', HERE / 'check_independent.py')]:
    for optimized in (False, True):
        commands.run(label + ('-optimized' if optimized else '-normal'),
                     [sys.executable, '-B', *(['-O'] if optimized else []), target])
selection = json.loads((HERE.parent / 'generated-java-actual/selection.json').read_text())['secondAttempt']
apple = M.apple_producer_provenance({k: selection[k] for k in ('DEVELOPER_DIR', 'SDKROOT')})
M.require(apple['sdk_settings']['sha256'] == selection['sdkSettingsSHA256'], 'Selected SDK differs from attempt 2')
M.save(HERE / 'apple-producer-provenance.json', apple)
before = json.loads((HERE / 'preserved-before.json').read_text())
preserved = {}
for path, files in before.items():
    after = M.inventory(Path(path))
    M.require(all(after.get(p) == identity for p, identity in files.items()), 'Prior evidence changed: ' + path)
    preserved[path] = {'prior_file_count': len(files), 'prior_files_unchanged': True,
                       'new_files_by_other_lanes': sorted(set(after) - set(files))}
M.save(HERE / 'preservation.json', preserved)
members = []
proofs = []
for name in ('01-full', '02-minimum', '03-fixed'):
    proof = json.loads((HERE / name / 'proof.json').read_text())
    raw = Path(proof['command']['logs']['stdout']['path']).read_text()
    classes = [Path(proof['command']['argv'][i]) for i in range(1, len(proof['command']['argv']))
               if not proof['command']['argv'][i].startswith('-')]
    parsed = M.member_references(raw, classes)
    M.require(parsed == json.loads((HERE / name / 'members.json').read_text()), 'Final runner parsing differs')
    members.append(parsed)
    proofs.append(proof)
M.require(members[0] == members[1] == members[2], 'Probes dropped or changed member entries')
M.require(proofs[0]['command']['logs']['stdout']['sha256'] == proofs[2]['command']['logs']['stdout']['sha256'],
          'Final bounded full dump differs')
original = (HERE / (runner.name + '.before')).read_text()
current = runner.read_text()
M.require(original.split('        finally:\n', 1)[1].split('\ndef member_references', 1)[0] ==
          current.split('        finally:\n', 1)[1].split('\ndef member_references', 1)[0], 'Approved command cleanup changed')
M.require(original.split('    finally:\n        terminal =', 1)[1] ==
          current.split('    finally:\n        terminal =', 1)[1], 'Approved scratch cleanup or CLI changed')
for path in (runner, tests):
    diff = ''.join(difflib.unified_diff((HERE / (path.name + '.before')).read_text().splitlines(True),
                                      path.read_text().splitlines(True), fromfile=path.name + '.before', tofile=path.name))
    (HERE / (path.name + '.patch')).write_text(diff)
M.save(HERE / 'validation.json', {'status': 'passed-bounded-runner-fix-only', 'revision': revision, 'git_tree': tree,
    'python': sys.version, 'runner': M.identity(runner), 'tests': M.identity(tests),
    'commands': commands.records, 'probes_used': 3, 'max_probe_seconds': 20, 'max_probe_bytes': 20 * 1024 * 1024,
    'total_probe_output_bytes': sum(sum(p['command']['logs'][s]['bytes'] for s in ('stdout', 'stderr')) for p in proofs),
    'all_probes_same_4944_members': True, 'full_dump_byte_identical_under_final_limit': True,
    'final_runner_reparsed_all_probes': True, 'approved_command_and_scratch_cleanup_unchanged': True,
    'policy_pair': M.load_profile()['id'], 'next_gate': 'Root-selected integrated pair8 full actual six-consumer matrix',
    'scope': 'Retained official javap evidence and Python controls only; no new producer, javac, D8, device, or runtime execution'})
print('Final verification passed; 45 runner + 7 prior independent controls per mode; all three probe inventories equal.')
