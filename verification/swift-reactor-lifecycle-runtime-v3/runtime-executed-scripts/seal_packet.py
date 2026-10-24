#!/usr/bin/env python3
"""Freeze the prepared source/proof packet; runtime outputs may only be additive."""
import collect as c

assert not (c.HERE / 'pre-runtime-freeze.json').exists()
assert not (c.HERE / 'seal.json').exists()
files = {str(p.relative_to(c.HERE)): c.sha(p.read_bytes()) for p in sorted(c.HERE.rglob('*')) if p.is_file()}
freeze = {'schema': 'mixer.swift-lifecycle.runtime-v3-pre-runtime-freeze.1', 'candidateClosure': c.read_json(c.HERE / 'source-delta.json')['candidateClosure'], 'files': files, 'closureSHA256': c.sha(c.enc(files)), 'runtimeExecuted': False, 'rootFiniteRepresentationSelectionPending': True}
c.save(c.HERE / 'pre-runtime-freeze.json', freeze)
c.save(c.HERE / 'seal.json', freeze)
print(c.enc({'files': len(files), 'candidateClosure': freeze['candidateClosure'], 'packetClosure': freeze['closureSHA256'], 'preRuntimeFreezeSHA256': c.sha((c.HERE / 'pre-runtime-freeze.json').read_bytes()), 'sealSHA256': c.sha((c.HERE / 'seal.json').read_bytes())}).decode())
