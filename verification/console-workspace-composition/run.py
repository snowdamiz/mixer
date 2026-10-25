#!/usr/bin/env python3
"""Source-bound console host checks; no browser, capture or native execution."""
from pathlib import Path
import datetime, hashlib, json, subprocess
ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
out = BASE / 'attempts' / stamp
out.mkdir(parents=True, exist_ok=False)
paths = sorted([str(p.relative_to(ROOT)) for folder in ['console/src', 'console/tests']
                for p in (ROOT / folder).rglob('*') if p.is_file()] + [
                    'console/package.json', 'console/package-lock.json', 'console/tsconfig.json',
                    'console/vite.config.ts', 'hosted/lib/mixer_hosted/authorization/scope.ex',
                    'website/src/styles.css', 'website/public/assets/flick-128.webp',
                    'website/public/assets/favicon-32.png', 'console/public/assets/flick-128.webp',
                    'console/public/assets/favicon-32.png', str(Path(__file__).resolve().relative_to(ROOT))])
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def manifest(): return {name: digest(ROOT/name) for name in paths}
before = manifest()
(out/'sources.json').write_text(json.dumps(before, indent=2)+'\n')
commands = []
checks = [('node-version',['node','--version']), ('npm-version',['npm','--version']),
          ('elixir-version',['elixir','--version']), ('typecheck',['npm','run','typecheck']),
          ('tests',['npm','test']), ('build',['npm','run','build'])]
try:
    for name, argv in checks:
        result = subprocess.run(argv, cwd=ROOT/'console', capture_output=True, timeout=90)
        (out/(name+'.stdout')).write_bytes(result.stdout)
        (out/(name+'.stderr')).write_bytes(result.stderr)
        commands.append({'argv':argv, 'cwd':'console', 'exit_code':result.returncode,
                         'stdout_sha256':hashlib.sha256(result.stdout).hexdigest(),
                         'stderr_sha256':hashlib.sha256(result.stderr).hexdigest()})
        assert result.returncode == 0, name
    assert manifest() == before, 'source drift'
    cache=ROOT/'console/node_modules/.cache'
    leftovers=[str(p.relative_to(ROOT)) for p in cache.iterdir()
               if p.name.startswith(('mixer-workspace-app-','mixer-workspace-binding-'))]
    assert not leftovers, leftovers
    bundles={str(p.relative_to(ROOT)):digest(p) for p in (ROOT/'console/dist').rglob('*') if p.is_file()}
    result='passed'
except Exception as error:
    result='failed';bundles={};raise
finally:
    receipt={'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
             'source_tree_sha256':hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest(),
             'sources':before,'commands':commands,'status':result,'build_artifacts':bundles,
             'scope':'Solid route SSR, pure controller, real reactive binding and actual HTTP client host tests. No browser layout/accessibility, live identity, provider or GA acceptance.',
             'cleanup':'Owned app/binding compilation caches absent; HTTP test server closes all connections in finally. No browser/native/capture started.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':result,'receipt':str(out/'receipt.json')}))
