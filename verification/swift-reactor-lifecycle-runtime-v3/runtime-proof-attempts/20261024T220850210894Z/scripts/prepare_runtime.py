#!/usr/bin/env python3
"""Prepare and syntax-check the selected predecessor matrix without execution."""
import importlib.util
import collect as c
import run_runtime

for script in c.HERE.glob('*.py'):
    compile(script.read_text(), str(script), 'exec')
old = c.ROOT / 'verification/swift-reactor-lifecycle-runtime-v2/runtime-plan.json'
plan = run_runtime.plan()
assert plan == c.read_json(old)
assert len(plan) == 30
assert len([row for row in plan if row['family'] == 'focused']) == 4
c.save(c.HERE / 'runtime-plan.json', plan)
c.save(c.HERE / 'runtime-runner-preparation.json', {'schema': 'mixer.swift-lifecycle.v3-runtime-runner-preparation.1', 'candidateClosure': run_runtime.s.SOURCE, 'commandCount': 30, 'focusedContexts': 4, 'exactAuthoredLifecycleIdentitiesPerContext': 23, 'planByteStructureSameAsV2': True, 'rootSelectionSchemaRequired': 'mixer.swift-lifecycle-test-repair-runtime-selection.1', 'rootSelectionMustBindPreRuntimeFreezeSHA256': True, 'rootSelectionMustBindPreRuntimeSealSHA256': True, 'qualifiedCompilerAndNodeChecksRetained': True, 'fullNodeOracleAppleLoaderCacheCheckBeforeOracleRetained': True, 'failureStopsMatrixAndRetainsAllOutputs': True, 'allPythonScriptSyntaxChecked': True, 'runtimeExecuted': False, 'newNodeQualificationClaimed': False})
print('Prepared unchanged 30-command conditional matrix; no compiler or tests executed')
