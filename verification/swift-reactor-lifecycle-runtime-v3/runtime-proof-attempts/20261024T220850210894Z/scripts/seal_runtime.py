#!/usr/bin/env python3
"""Seal additive runtime evidence and the unchanged original source/proof freeze."""
import collect as c
import verify_runtime

assert not (c.HERE / 'runtime-final-seal.json').exists()
replay = verify_runtime.verify()
receipt = c.read_json(c.HERE / 'runtime-receipt.json')
assert receipt['readOnlyReplaySHA256'] == c.sha((c.HERE / 'runtime-read-only-replay.json').read_bytes())
assert receipt['selectedMatrixComplete'] == replay['selectedMatrixComplete']
files = {str(p.relative_to(c.HERE)): c.sha(p.read_bytes()) for p in sorted(c.HERE.rglob('*')) if p.is_file()}
seal = {'schema': 'mixer.swift-lifecycle.runtime-v3-final-seal.1', 'candidateClosure': replay['candidateClosure'], 'preRuntimeFreezeSHA256': c.sha((c.HERE / 'pre-runtime-freeze.json').read_bytes()), 'preRuntimeSealSHA256': c.sha((c.HERE / 'seal.json').read_bytes()), 'rootRuntimeSelectionSHA256': verify_runtime.SELECTION_SHA, 'files': files, 'closureSHA256': c.sha(c.enc(files)), 'selectedRuntimeMatrixComplete': replay['selectedMatrixComplete'], 'fullPlannedSLRowsComplete': False, 'rootRuntimeAcceptancePending': True}
c.save(c.HERE / 'runtime-final-seal.json', seal)
print(c.enc({'files': len(files), 'closureSHA256': seal['closureSHA256'], 'runtimeFinalSealSHA256': c.sha((c.HERE / 'runtime-final-seal.json').read_bytes()), 'selectedRuntimeMatrixComplete': seal['selectedRuntimeMatrixComplete']}).decode())
