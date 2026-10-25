#!/usr/bin/env python3
"""Restore this packet's exact owned source/executable only; never build or execute them."""
import gzip
import hashlib
import json
import subprocess
import sys
from packetlib import HERE as H, archive_payloads, read, write_source

subprocess.run([sys.executable, '-B', str(H / 'verify.py')], check=True, timeout=30)
scratch, binary = H / 'owned-scratch', H / 'bin/exact-tests'
assert not scratch.exists() and not binary.exists()
assert not (H / 'root-selection.json').exists() and not (H / 'target-attempt-started.json').exists()
manifest = read(H / 'copied-build-manifest.json')
source = archive_payloads(H / 'prepared-source.tar.gz', manifest)
info = read(H / 'binary.json')['retained']
assert 0 < info['bytes'] <= 16 * 1024 * 1024
with gzip.open(str(binary) + '.gz', 'rb') as stream:
    data = stream.read(info['bytes'] + 1)
assert len(data) == info['bytes'] and hashlib.sha256(data).hexdigest() == info['sha256']
assert binary.parent.is_dir() and not binary.parent.is_symlink()
scratch.mkdir(mode=0o700)
(scratch / 'tmp').mkdir(mode=0o700)
write_source(source, scratch / 'vm')
with binary.open('xb') as stream:
    stream.write(data)
binary.chmod(0o700)
print(json.dumps({'exactOwnedSourceAndBinaryRestored':True, 'sourceManifestFiles':len(manifest),
                  'binarySHA256':info['sha256'], 'rootSelectionCreated':False,
                  'fullTargetAttempts':0, 'compilerExecuted':False,
                  'nextStep':'root independently reviews accepted independent review and makes fresh exact selection'}))
