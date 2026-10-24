#!/usr/bin/env python3
"""Remove only this packet's metadata scratch after empty holder/process checks."""
from pathlib import Path
import shutil, subprocess
import collect as c

session = c.read_json(c.HERE / 'metadata-tool-session.json')
scratch = Path(session['scratch'])
assert scratch.name.startswith('mixer-lifecycle-v3-metadata-')
assert c.sha(Path(session['binary']).read_bytes()) == session['sha256']
holder = subprocess.run(['/usr/sbin/lsof', '-nP', '+D', str(scratch)], capture_output=True)
c.save(c.HERE / 'metadata-tool-cleanup.stdout', holder.stdout)
c.save(c.HERE / 'metadata-tool-cleanup.stderr', holder.stderr)
assert holder.returncode == 1 and not holder.stdout and not holder.stderr
commands = subprocess.check_output(['/bin/ps', '-axo', 'pid=,pgid=,command='], text=True)
assert not any(str(scratch) in row and 'ps -axo' not in row for row in commands.splitlines())
files = [x for x in scratch.rglob('*') if x.is_file()]
count, size = len(files), sum(x.stat().st_size for x in files)
shutil.rmtree(scratch)
c.save(c.HERE / 'metadata-tool-cleanup.json', {'scratch': str(scratch), 'removed': not scratch.exists(), 'filesRemoved': count, 'logicalBytesRemoved': size, 'holderCheckEmpty': True, 'processReferencesEmpty': True, 'sharedInstallModified': False, 'nativeInstancesCreated': 0})
pins = []
baseline_query = c.read_json(c.ROOT / 'verification/swift-reactor-lifecycle-runtime-v2/exact-query-swift-debug-unit.json')
baseline = c.read_json(c.ROOT / 'verification/swift-reactor-lifecycle-runtime-v2' / baseline_query['attempt'] / 'tools.json')['actualCompiler']
sysroot = Path(session['sysroot'])
actual = {str(p.relative_to(sysroot)): c.sha(p.read_bytes()) for group in ['bin', 'lib'] for p in sorted((sysroot / group).rglob('*')) if p.is_file()}
assert actual == baseline['sysrootCompilerFiles']
for attempt in sorted((c.HERE / 'attempts').iterdir()):
    tools = c.read_json(attempt / 'tools.json')
    command = c.read_json(attempt / 'command.json')
    cleanup = c.read_json(attempt / 'cleanup.json')
    assert tools['actualCompiler'] == baseline
    assert cleanup['removed'] and cleanup['holderCheckEmpty'] and not cleanup['remainingGroup']
    assert command['sourceUnchanged'] and command['exitCode'] == 0 and not command['remainingGroup']
    pins.append({'attempt': str(attempt.relative_to(c.HERE)), 'exactOriginalCompilerAndAllBinLibFiles': True, 'exitCode': command['exitCode'], 'sourceUnchanged': True, 'cleanupComplete': True})
assert len(pins) == 5
c.save(c.HERE / 'compiler-pin-and-command-cleanup-proof.json', pins)
print('All five targets and owned metadata scratch cleaned; original compiler bin/lib still exact')
