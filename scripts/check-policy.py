#!/usr/bin/env python3
"""Dependency and acceptance guardrail. Not a legal or security audit."""
from pathlib import Path
import json
import os
import re
import sys

root = Path(__file__).resolve().parents[1]
excluded = {'.git', '.build', 'target', 'node_modules', '.gradle', '.mixer', 'local'}
manifests = {'Package.swift', 'Package.resolved', 'Cargo.toml', 'Cargo.lock', 'package.json', 'package-lock.json', 'go.mod', 'go.sum', 'build.gradle', 'build.gradle.kts', 'settings.gradle.kts'}
prohibited = re.compile(r'(skiptools[/.:]|patch-release[/.:]|skipstone|skip-fuse|skip-ui|patch-swift|wasmkit|wasmtime|wasmer|wasm3)', re.I)
failures = []
inspected = []
paths = []
for directory, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in excluded]
    paths.extend(Path(directory) / f for f in files)
for path in paths:
    if path.name not in manifests:
        continue
    inspected.append(str(path.relative_to(root)))
    content = path.read_text(errors='replace')
    for line_number, line in enumerate(content.splitlines(), 1):
        if prohibited.search(line):
            failures.append(f'{path.relative_to(root)}:{line_number}: prohibited engine/dependency reference')

gates = json.loads((root / 'gates/ga.json').read_text())['gates']
if [g['id'] for g in gates] != [f'G{i:02}' for i in range(1, 39)]:
    failures.append('G01–G38 must remain intact and ordered')
for gate in gates:
    if gate['status'] not in {'planned', 'running', 'passed', 'failed', 'blocked'}:
        failures.append(f"{gate['id']}: invalid status")
    if gate['status'] == 'passed' and (not gate['evidence'] or not gate['reviewer']):
        failures.append(f"{gate['id']}: passed gate lacks evidence/reviewer")

packages = json.loads((root / 'work-graph.json').read_text())['packages']
if [p['id'] for p in packages] != [f'W{i:02}' for i in range(1, 19)]:
    failures.append('W01–W18 must remain intact and ordered')
print(json.dumps({'status': 'failed' if failures else 'passed', 'scope': 'manifest-and-gate-guardrail-only', 'manifests': sorted(inspected), 'failures': failures}, indent=2))
sys.exit(bool(failures))
