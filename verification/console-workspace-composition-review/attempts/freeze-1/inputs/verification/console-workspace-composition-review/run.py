#!/usr/bin/env python3
"""Bounded independent host review; copies only console/branding inputs.

No hosted application, frozen lane, browser, DOM automation, capture, or native
instance is read or started. Every attempt is retained, including failed output.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(manifest: dict[str, str]) -> str:
    return hashlib.sha256(''.join(f'{key}\0{value}\n' for key, value in sorted(manifest.items())).encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('attempt')
    parser.add_argument('--source-freeze', default='not frozen; preliminary only')
    args = parser.parse_args()
    if not args.attempt or '/' in args.attempt or args.attempt in ['.', '..']:
        raise SystemExit('Attempt must be one new directory name')
    target = BASE / 'attempts' / args.attempt
    target.mkdir(parents=True, exist_ok=False)
    inputs = target / 'inputs'
    inputs.mkdir()
    paths = [ROOT / 'AGENTS.md', ROOT / 'PLAN.md']
    paths.extend(sorted(path for path in (ROOT / 'console/src').rglob('*') if path.is_file()))
    paths.extend(sorted(path for path in (ROOT / 'console/tests').iterdir() if path.is_file()))
    paths.extend(ROOT / 'console' / name for name in ['package.json', 'package-lock.json', 'tsconfig.json', 'vite.config.ts'])
    paths.extend(ROOT / prefix / name for prefix in ['website/public/assets', 'console/public/assets'] for name in ['flick-128.webp', 'favicon-32.png'])
    paths.append(ROOT / 'website/src/styles.css')
    paths.extend(BASE / name for name in ['run.py', 'reactive-review.mjs', 'ssr-review.mjs', 'render-review.tsx', 'build-ssr.mjs'])
    manifest = {str(path.relative_to(ROOT)): sha(path) for path in paths}
    for path in paths:
        destination = inputs / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    commands = []
    scratch = Path(tempfile.mkdtemp(prefix='scratch-', dir=target))
    dependencies = ROOT / 'console/node_modules'
    links = [inputs / 'node_modules', inputs / 'console/node_modules', scratch / 'runtime/node_modules', scratch / 'ssr/node_modules']
    for link in links:
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(dependencies, target_is_directory=True)
    for directory in ['runtime', 'ssr']:
        (scratch / directory / 'package.json').write_text('{"type":"module"}\n')
    receipt = {'scope': 'Independent console composition host review; no deployment/GA/native/browser acceptance',
               'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'source_freeze': args.source_freeze,
               'source_manifest': manifest, 'source_tree_sha256': tree_digest(manifest), 'commands': commands,
               'limitations': ['No browser/DOM/UI automation/capture', 'No simulator/emulator/physical-phone runtime',
                               'No hosted/default Endpoint/Repo integration, provider, deployment, store, signing, or GA acceptance',
                               'External login/session adapter still not implemented; synthetic immutable session values only'],
               'processes_started': 'Bounded Python, Node, TypeScript and Vite commands only; no listeners/native/capture processes'}

    def run(name: str, command: list[str], cwd: Path = ROOT, env: dict[str, str] | None = None) -> int:
        index = len(commands) + 1
        prefix = target / f'{index:02d}-{name}'
        started = time.monotonic()
        try:
            result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, timeout=90)
            code, stdout, stderr = result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as error:
            code, stdout, stderr = 124, error.stdout or b'', (error.stderr or b'') + b'\nTimed out after 90 seconds.\n'
        prefix.with_suffix('.stdout').write_bytes(stdout)
        prefix.with_suffix('.stderr').write_bytes(stderr)
        commands.append({'name': name, 'command': command, 'cwd': str(cwd), 'returncode': code,
                         'duration_seconds': round(time.monotonic() - started, 4),
                         'stdout': str(prefix.with_suffix('.stdout').relative_to(target)),
                         'stderr': str(prefix.with_suffix('.stderr').relative_to(target))})
        print(f'{name}: exit {code}', flush=True)
        return code

    success = True
    try:
        run('revision', ['git', 'rev-parse', 'HEAD'])
        run('node-version', ['node', '--version'])
        run('python-version', [sys.executable, '--version'])
        run('typescript-version', ['node', str(dependencies / 'typescript/bin/tsc'), '--version'])
        run('vite-version', ['node', str(dependencies / 'vite/bin/vite.js'), '--version'])
        run('dependency-versions', ['node', '--input-type=module', '-e',
            'import fs from "node:fs"; for (const name of ["solid-js","@solidjs/router","vite-plugin-solid"]) '
            'console.log(name + " " + JSON.parse(fs.readFileSync("node_modules/"+name+"/package.json", "utf8")).version);'], cwd=inputs / 'console')
        selected = ['tests/workspace-controller.test.mjs', 'tests/workspace-binding.test.mjs', 'tests/workspace-app.test.mjs', 'tests/brand-parity.test.mjs']
        success &= run('producer-selected-replay', ['node', '--test', *selected], cwd=inputs / 'console') == 0
        success &= run('binding-compile', ['node', str(dependencies / 'typescript/bin/tsc'),
            'src/state/workspace-binding.ts', '--target', 'ES2022', '--module', 'ESNext', '--moduleResolution', 'Bundler',
            '--strict', '--skipLibCheck', '--noUncheckedIndexedAccess', '--exactOptionalPropertyTypes', '--outDir', str(scratch / 'runtime')],
            cwd=inputs / 'console') == 0
        env = {**os.environ, 'MIXER_REVIEW_DEPENDENCIES': str(dependencies), 'MIXER_REVIEW_RUNTIME': str(scratch / 'runtime'),
               'MIXER_REVIEW_CONSOLE': str(inputs / 'console'),
               'MIXER_REVIEW_ENTRY': str(inputs / BASE.relative_to(ROOT) / 'render-review.tsx'),
               'MIXER_REVIEW_SSR_OUT': str(scratch / 'ssr'), 'MIXER_REVIEW_SSR': str(scratch / 'ssr/render-review.js')}
        success &= run('independent-reactive', ['node', '--conditions=browser', '--test', str(inputs / BASE.relative_to(ROOT) / 'reactive-review.mjs')], env=env) == 0
        ssr_built = run('ssr-compile', ['node', str(inputs / BASE.relative_to(ROOT) / 'build-ssr.mjs')], env=env) == 0
        success &= ssr_built
        if ssr_built:
            success &= run('independent-ssr', ['node', '--test', str(inputs / BASE.relative_to(ROOT) / 'ssr-review.mjs')], env=env) == 0
        after = {str(path.relative_to(ROOT)): sha(path) for path in paths}
        receipt['live_source_unchanged'] = after == manifest
        receipt['source_manifest_after'] = after
        success &= after == manifest
    finally:
        for link in links:
            if link.is_symlink(): link.unlink()
        shutil.rmtree(scratch)
        receipt['cleanup'] = {'scratch_removed': not scratch.exists(), 'dependency_symlinks_removed': all(not path.is_symlink() for path in links),
                              'native_or_capture_started': False, 'owned_listener_started': False,
                              'unrelated_processes_or_resources_modified': False}
        receipt['completed_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
        receipt['passed'] = bool(success)
        (target / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
