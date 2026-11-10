"""Independent CURRENT oracle for host tests; never imported by product code.

The prospective caller binding selects the current profile. Historical transition
maps remain explicit; this reader neither derives expectations from Swift nor
advances source identities, reviews, or qualification.
"""
import hashlib
import json
from pathlib import Path

BINDING = Path('verification/plan-continuation-2026-11-07/source113-inspection-caller-r3/binding.json')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeError('Duplicate current-profile metadata key: ' + key)
        result[key] = value
    return result


def load_current_profile(root):
    binding = json.loads((root / BINDING).read_bytes(), object_pairs_hook=unique_object)
    summary = binding['profile']
    # The summary selects CURRENT; historical transition names/numbers are data.
    candidates = [value['profileAfter'] for value in binding.values()
                  if isinstance(value, dict) and isinstance(value.get('profileAfter'), dict)
                  and value['profileAfter'].get('id') == summary['id']]
    if len(candidates) != 1:
        raise RuntimeError('Current-profile metadata must select one exact transition')
    profile = candidates[0]
    observed = {'id': profile['id']}
    for kind in ('sdk', 'adapter'):
        files = profile[kind + '_files']
        digest = hashlib.sha256(''.join(path + '\0' + row['sha256'] + '\n'
                                      for path, row in sorted(files.items())).encode()).hexdigest()
        if digest != profile[kind + '_compatibility_sha256']:
            raise RuntimeError('Current-profile metadata projection differs: ' + kind)
        observed[kind + '_count'] = len(files)
        observed[kind + '_sha256'] = digest
    observed['java_sources'] = len([p for p in profile['adapter_files'] if p.endswith('.java')])
    if summary != observed:
        raise RuntimeError('Current-profile metadata summary differs from exact roster')
    return profile
