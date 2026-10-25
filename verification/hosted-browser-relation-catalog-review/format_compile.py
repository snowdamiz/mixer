"""Actual projectless formatting, WAE compilation and source-closure adversity."""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
manifest = 'hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex'
catalog = 'hosted/lib/mixer_hosted/browser_auth/relation_catalog.ex'
review = 'verification/hosted-browser-relation-catalog-review/live.exs'
data = json.loads((ROOT / 'hosted/priv/browser_auth/relation_surface_v1_pg16.json').read_text())
paths = list(data['source_bindings']) + [manifest, catalog] + [f'hosted/priv/browser_auth/relation_surface_v1_pg{major}.json' for major in [16, 17]]
env = dict(os.environ, ERL_FLAGS='+S 2:2')
depdirs = [ROOT / 'hosted/_build/test/lib' / dep / 'ebin' for dep in ['telemetry','decimal','db_connection','ecto','ecto_sql','postgrex','jason','oban']]
flags = [value for dep in depdirs for value in ['-pa', str(dep)]]
receipt = {'commands': [], 'scope': 'Projectless format, selected WAE compile, compile-time source closure and relocated compiled runtime; no app boot or server.'}
scratch = Path(tempfile.mkdtemp(prefix='mixer-relation-review-compile-'))


def run(label, command, cwd, expected=0):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, timeout=45)
    (BASE / (label + '.stdout')).write_bytes(result.stdout)
    (BASE / (label + '.stderr')).write_bytes(result.stderr)
    receipt['commands'].append({'label': label, 'command': command, 'cwd': str(cwd), 'exit': result.returncode, 'expected': expected})
    if expected == 0:
        assert result.returncode == 0, label
    else:
        assert result.returncode != 0, label
    return result


try:
    format_dir = scratch / 'format'
    format_dir.mkdir()
    for path in [manifest, catalog, review]:
        shutil.copy2(ROOT / path, format_dir / Path(path).name)
    run('projectless-format', ['mix', 'format', '--check-formatted', 'relation_manifest.ex', 'relation_catalog.ex', 'live.exs'], format_dir)
    source = scratch / 'source'
    for path in paths:
        target = source / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / path, target)
    beam = scratch / 'beams'
    beam.mkdir()
    compile_command = ['elixirc'] + flags + ['--warnings-as-errors', '-o', str(beam), str(source / manifest), str(source / catalog)]
    run('selected-wae-compile', compile_command, scratch)
    for name, relative, change in [
        ('changed-source', 'hosted/lib/mixer_hosted/customer_artifacts/schema.ex', lambda p: p.write_bytes(p.read_bytes() + b'\n# independent altered source\n')),
        ('missing-oban-source', 'hosted/deps/oban/lib/oban/migrations/postgres/v14.ex', lambda p: p.unlink()),
        ('changed-pg17-manifest', 'hosted/priv/browser_auth/relation_surface_v1_pg17.json', lambda p: p.write_bytes(p.read_bytes() + b'\n')),
    ]:
        target = source / relative
        original = target.read_bytes()
        change(target)
        isolated = scratch / name
        isolated.mkdir()
        run(name, ['elixirc'] + flags + ['--warnings-as-errors', '-o', str(isolated), str(source / manifest), str(source / catalog)], scratch, expected=1)
        target.write_bytes(original)
    # Remove every source/JSON/verification resource before loading the beams.
    shutil.rmtree(source)
    shutil.rmtree(format_dir)
    assert not any(p.suffix in ['.ex','.exs','.json'] for p in scratch.rglob('*') if p.is_file())
    run('relocated-runtime-no-source', ['elixir'] + flags + ['-pa', str(beam), '-e', 'for major <- [16,17] do m=MixerHosted.BrowserAuth.RelationManifest.for_major(major); 9=map_size(m["structure"]["relations"]); 80=length(m["check_keys"]) end; 31=length(Keyword.get_values(MixerHosted.BrowserAuth.RelationManifest.__info__(:attributes),:external_resource) |> List.flatten()); IO.puts("compiled manifests load without source or verification files")'], scratch)
    receipt['source_sha256'] = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths + [review]}
    receipt['passed'] = True
finally:
    shutil.rmtree(scratch)
    receipt['cleanup'] = {'scratch_absent': not scratch.exists()}
    (BASE / 'format-compile.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print('projectless formatting and selected compilation/closure controls pass')
