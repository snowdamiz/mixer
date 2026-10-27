#!/usr/bin/env python3
"""Run only the selected console host roster in an owned, bounded process group."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(__file__).resolve().parent
COMMANDS = {
    'focused': ['node', '--test', 'tests/browser-session-client.test.mjs', 'tests/browser-session-controller.test.mjs', 'tests/browser-session-binding.test.mjs'],
    'regression': ['npm', 'test'],
    'typecheck': ['npm', 'run', 'typecheck'],
    'build': ['npm', 'run', 'build'],
    'controller-binding': ['node', '--test', 'tests/browser-session-controller.test.mjs', 'tests/browser-session-binding.test.mjs'],
    'binding': ['node', '--test', 'tests/browser-session-binding.test.mjs'],
    'client': ['node', '--test', 'tests/browser-session-client.test.mjs'],
    'controller': ['node', '--test', 'tests/browser-session-controller.test.mjs'],
}

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

def manifest():
    paths = set(git('ls-files', 'console').splitlines())
    paths.update(str(path.relative_to(ROOT)) for pattern in ['console/src/api/browser-session-client.ts', 'console/src/state/browser-session-*.ts', 'console/tests/browser-session-*.mjs'] for path in ROOT.glob(pattern))
    paths.update(['website/src/styles.css', 'website/public/assets/flick-128.webp', 'website/public/assets/favicon-32.png',
                  'hosted/lib/mixer_hosted/authorization/scope.ex', 'AGENTS.md', 'mixer-product-plan.md',
                  'verification/console-session-integration-selection/frontend-contract.json', 'verification/console-session-integration-selection/selection.md'])
    entries = [{'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), 'bytes': (ROOT / path).stat().st_size} for path in sorted(paths)]
    digest = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'revision': git('rev-parse', 'HEAD'), 'tracked_tree': git('rev-parse', 'HEAD^{tree}'), 'source_digest_sha256': digest, 'files': entries}

def run(command, directory, label, cap=55):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    begin = time.monotonic()
    stdout, stderr = directory / (label + '.stdout.txt'), directory / (label + '.stderr.txt')
    with stdout.open('wb') as out, stderr.open('wb') as err:
        child = subprocess.Popen(command, cwd=ROOT / 'console', stdout=out, stderr=err, start_new_session=True)
        pid, pgid = child.pid, os.getpgid(child.pid)
        timed_out = False
        try:
            code = child.wait(timeout=cap)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(pgid, signal.SIGTERM)
            try: code = child.wait(timeout=1)
            except subprocess.TimeoutExpired:
                os.killpg(pgid, signal.SIGKILL)
                code = child.wait(timeout=1)
        # Only this captured group is inspected/cleaned. No global process inventory.
        remaining = False
        try:
            os.killpg(pgid, 0)
            remaining = True
            os.killpg(pgid, signal.SIGTERM)
            time.sleep(0.1)
            try: os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError: pass
        except ProcessLookupError: pass
        try: os.killpg(pgid, 0); empty = False
        except ProcessLookupError: empty = True
    return {'command': command, 'cwd': str(ROOT / 'console'), 'started_at': started, 'wall_seconds': round(time.monotonic() - begin, 3),
            'pid': pid, 'pgid': pgid, 'wall_cap_seconds': cap, 'timed_out': timed_out, 'exit_code': code,
            'stdout': stdout.name, 'stderr': stderr.name, 'cleanup': {'captured_group_only': True, 'descendants_seen_after_parent_exit': remaining, 'group_absent_after_cleanup': empty}}

mode = sys.argv[1]
if mode not in COMMANDS: raise SystemExit('Unknown selected host command')
attempt = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-' + mode
directory = EVIDENCE / 'attempts' / attempt
directory.mkdir(parents=True)
inputs = manifest()
(directory / 'inputs.json').write_text(json.dumps(inputs, indent=2) + '\n')
versions = []
for label, command in [('node-version', ['node', '--version']), ('npm-version', ['npm', '--version']),
                       ('typescript-version', ['node', 'node_modules/typescript/bin/tsc', '--version']), ('vite-version', ['node', 'node_modules/vite/bin/vite.js', '--version'])]:
    item = run(command, directory, label, cap=8)
    item['output'] = (directory / item['stdout']).read_text() + (directory / item['stderr']).read_text()
    versions.append(item)
if mode == 'regression':
    item = run(['elixir', '--version'], directory, 'elixir-version', cap=8)
    item['output'] = (directory / item['stdout']).read_text() + (directory / item['stderr']).read_text()
    versions.append(item)
result = run(COMMANDS[mode], directory, 'command')
result.update({'schema': 1, 'mode': mode, 'source': inputs, 'python': sys.version, 'tool_versions': versions,
               'scope': 'host Node tests, strict TypeScript and/or production bundle only; synthetic metadata/EventTargets and actual Solid host runtime; standalone Elixir Scope parity only in full existing regression',
               'paused_unrun': ['browser/UI/capture', 'native simulator/emulator', 'physical phones'],
               'no_git_mutation_or_publication': True, 'no_global_process_inventory': True})
(directory / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'directory': str(directory), 'exit_code': result['exit_code'], 'timed_out': result['timed_out'], 'wall_seconds': result['wall_seconds'], 'source_digest': inputs['source_digest_sha256'], 'cleanup': result['cleanup']}))
print((directory / 'command.stdout.txt').read_text()[-18000:])
print((directory / 'command.stderr.txt').read_text()[-8000:])
raise SystemExit(1 if result['timed_out'] else result['exit_code'])
