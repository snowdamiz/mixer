#!/usr/bin/env python3
"""Restore the exact retained metadata-only tool into owned disposable scratch."""
from pathlib import Path
import gzip, os, subprocess, tempfile
import collect as c

old = c.ROOT / 'verification/swift-reactor-lifecycle-accounting'
build = c.read_json(old / 'layout-driver-build.json')
raw = gzip.decompress((old / build['attempt'] / 'layout-driver.gz').read_bytes())
assert c.sha(raw) == build['sha256'] == '80c8c8410b4e79120dec1368ad368f869119aeface40f8660e7bd19527c878b7'
scratch = Path(tempfile.mkdtemp(prefix='mixer-lifecycle-v3-metadata-'))
binary = scratch / 'layout-driver'
binary.write_bytes(raw)
binary.chmod(0o755)
result = subprocess.run(['/usr/bin/otool', '-L', str(binary)], capture_output=True)
c.save(c.HERE / 'metadata-tool-otool.stdout', result.stdout)
c.save(c.HERE / 'metadata-tool-otool.stderr', result.stderr)
assert result.returncode == 0
sysroot = subprocess.check_output(['/opt/homebrew/opt/rustup/bin/rustc', '--print', 'sysroot'], text=True).strip()
c.save(c.HERE / 'metadata-tool-session.json', {'scratch': str(scratch), 'binary': str(binary), 'sha256': c.sha(raw), 'originalArchivedBuild': build, 'sysroot': sysroot, 'otoolExitCode': result.returncode, 'networkUsed': False, 'sharedInstallModified': False})
print('Restored exact metadata-only driver into owned scratch')
