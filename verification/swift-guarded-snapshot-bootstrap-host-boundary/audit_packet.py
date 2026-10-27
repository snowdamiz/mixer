#!/usr/bin/env python3
"""Pure checks on this packet's exact source, compiler outputs and limitations."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def main():
    checks=0
    def require(value):
        nonlocal checks
        assert value
        checks+=1
    inventory=json.loads((HERE/'driver-inventory.json').read_text())
    source=json.loads((HERE/'source-manifest.json').read_text())
    layout=json.loads((HERE/'layout-source-manifest.json').read_text())
    model=json.loads((HERE/'ordering-results.json').read_text())
    include=(HERE/'driver.inc.rs').read_text()
    require(inventory['scaffold_sha256']==sha(include.encode()))
    require(inventory['driver_mir_sha256']==sha((HERE/'driver.mir').read_bytes()))
    require(inventory['role_count']==30)
    require(inventory['logical_source_object_union_bytes']==95_850)
    require(inventory['parameter_source_object_bytes']==1344)
    require(sum(r['bytes'] for r in inventory['roles'])==95_850)
    require(sum(r['kind']=='parameter' for r in inventory['roles'])==7)
    require(len(inventory['actual_type_sizes'])==21)
    require(len({r['local'] for r in inventory['roles']})==30)
    require(source['source_tree_sha256']==sha(canonical(source['members'])))
    require(layout['source_tree_sha256']==sha(canonical(layout['members'])))
    require(inventory['source_tree_sha256']==source['source_tree_sha256'])
    require(len(source['members'])==144 and len(layout['members'])==144)
    require(source['new_driver_identity_separate_from_historical_host11'])
    a={r['path']:r for r in source['members']};b={r['path']:r for r in layout['members']}
    require(sorted(n for n in a if a[n]!=b[n])==['src/experimental_swift_reactor/cache/initial_profile_v1.rs','src/lib.rs'])
    require('#[cfg(mixer_bootstrap_one_fixture_v1)]' in include)
    require('#[test]' not in include and '#[no_mangle]' not in include and 'extern ' not in include)
    require('selected: super::super::retained_profile_loader_v1::SelectedValidatedProfileV1' in include)
    require('pub(in crate::experimental_swift_reactor)' in include)
    require(include.count('selected.into_snapshot_scope_v1(')==1)
    require(include.count('scope.construct_v1(')==1)
    require(include.count('run.outer_v1(')==1)
    require(include.count('run.finish_v1(')==1)
    require('attach_wasi' not in include and 'OpenOptions' not in include and 'assert!' not in include and 'panic!' not in include)
    for name,code in [('leaf-metadata-mir',0),('leaf-layout-queries',1)]:
        p=HERE/'commands'/name
        r=json.loads((p/'receipt.json').read_text())
        require(r['exit_code']==code and r['expectation_met'] and r['direct_child_waited'])
        require('--test' not in r['argv'] and '--crate-type' in r['argv'])
        require('mixer_bootstrap_one_fixture_v1' in r['argv'])
        require(not any(x.startswith('--emit=link') for x in r['argv']))
    require((HERE/'commands/leaf-layout-queries/stderr').read_text().count('error[E0308]')==21)
    require(model['controls_passed']==157)
    require(model['source_sha256']==sha((HERE/'ordering_model.py').read_bytes()))
    require(model['product_limits']==dict(work=1_000_000_000,combined_storage=268_435_456))
    require(not model['host_authority_created'] and not model['product_or_loader_executed'])
    require(not model['partial_logical_union_is_complete_host_storage_quote'])
    cleanup=json.loads((HERE/'compiler-cleanup.json').read_text())
    require(cleanup['owned_scratch_removed'] and not (HERE/'owned-work').exists())
    require(cleanup['product_executables_created']==0 and cleanup['product_executables_executed']==0)
    require(not cleanup['global_process_inventory'])
    result=dict(schema=1,controls_passed=checks,
                scope='pure source/custody/own compiler artifact assertions; no release permission',
                source_sha256=sha(Path(__file__).read_bytes()))
    (HERE/'audit-results.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    main()
