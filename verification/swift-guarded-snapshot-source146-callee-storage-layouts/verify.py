"""Read-only validation of the one retained compiler observation."""
import hashlib
import json
from pathlib import Path
import re

D = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(name):
    return json.loads((D / name).read_text())


def main():
    selection = read('selection.json')
    results = read('results.json')
    receipt = read('compiler-receipt.json')
    binding = read('binding.json')
    closure = read('compiled-manifest.json')
    cleanup = read('cleanup.json')
    assert receipt['exit_code'] == 1 and not receipt['timed_out']
    assert receipt['direct_child_waited'] and receipt['owned_group_absent']
    assert cleanup['completed'] and cleanup['owned_scratch_removed']
    assert cleanup['removed_files'] == 146 and not (D / 'owned-work').exists()
    assert not results['metadata_produced'] and not results['product_executed']
    assert len(selection['queries']) == len(results['queries']) == 21
    for name, identity in receipt['outputs'].items():
        data = (D / ('compiler.' + name)).read_bytes()
        assert len(data) == identity['bytes'] and sha(data) == identity['sha256']
    data_names = ['compiled-manifest.json', 'argv.bin', 'environment.bin', None, 'compiler-version.stdout']
    key_names = ['MIXER_LOADER_MANIFEST_SHA256', 'MIXER_LOADER_COMMAND_SHA256', 'MIXER_LOADER_COMPILE_ENV_SHA256', 'MIXER_LOADER_COMPILER_SHA256', 'MIXER_LOADER_COMPILER_VERSION_SHA256']
    for key, name in zip(key_names, data_names):
        expected = closure['compiler_sha256'] if name is None else sha((D / name).read_bytes())
        assert binding['compile_identity_keys'][key] == receipt['environment'][key] == expected
    found = {}
    for line in (D / 'compiler.stderr').read_text().splitlines():
        msg = json.loads(line)
        if msg['level'] == 'error' and msg.get('code'):
            assert msg['code']['code'] == 'E0308'
            declarations = [line['text'] for span in msg['spans'] for line in span['text']]
            names = set(re.findall(r'LP_(SIZE|ALIGN)_(\d+)', '\n'.join(declarations)))
            assert len(names) == 1
            kind, index = names.pop()
            size_messages = [span['label'] for span in msg['spans'] if span['is_primary'] and span.get('label') and 'found one with a size' in span['label']]
            assert len(size_messages) == 1
            actual = int(re.search(r'found one with a size of (\d+)', size_messages[0])[1])
            key = (int(index), kind)
            assert key not in found
            found[key] = actual
    assert len(found) == 42
    for index, row in enumerate(results['queries']):
        assert row['concrete'] == selection['queries'][index]['concrete']
        assert row['size'] == found[(index, 'SIZE')]
        assert row['alignment'] == found[(index, 'ALIGN')]
    old = {r['path']: r for r in closure['source_manifest']['members']}
    new = {r['path']: r for r in closure['compiled_source_members']}
    assert len(old) == len(new) == 146
    assert [name for name in old if old[name] != new[name]] == [selection['append_to']]
    assert new[selection['append_to']]['bytes'] == old[selection['append_to']]['bytes'] + (D / 'layout-queries.inc.rs').stat().st_size
    if (D / 'seal.json').exists():
        for row in read('seal.json')['members']:
            data = (D / row['path']).read_bytes()
            assert len(data) == row['bytes'] and sha(data) == row['sha256']
    print(json.dumps(dict(status='passed', layouts=21, actual_diagnostics=42, changed_source_members=1, anonymous_closure_observations=0, product_runtime=False)))


if __name__ == '__main__':
    main()
