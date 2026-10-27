#!/usr/bin/env python3
"""Read-only custody verification of the explicitly released input packets."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    expected = {
        'verification/swift-semantic-adapter-root-review/guarded-snapshot-funding-host-acceptance.json':
            '17789ef30bb818f91a928941162029a12c75ca7dddd33e8cfc073ec4950a615f',
        'verification/swift-semantic-adapter-root-review/guarded-snapshot-full-work-host-acceptance.json':
            'ca79a84f7c6aa4277ca9a00a5f64c8d214a3c43c051a14577b9614a39b1a59b9',
        'verification/swift-semantic-adapter-root-review/real-loader-host-acceptance.json':
            '6c579a2a868bb2eb8ba94f7680355171d28ade46f5a5c89ebf96f014915eeb70',
        'verification/swift-guarded-snapshot-funding-implementation/seal.json':
            'e006b90b8c9e351e0d4dd504c6de309e2c7970b628fe9fc4f788cb30e77bedf7',
        'verification/swift-guarded-snapshot-funding-independent/seal.json':
            'e971c908328ef36e8e5c582fd84d01999c1c4ddce473819b673cfda5ef48a8fc',
        'verification/swift-guarded-snapshot-complete-work-plan/seal.json':
            '7198ae0748ce0c8c576afc953aef8f3827b0a0d925ea246225245ba4cf000a27',
        'verification/swift-guarded-snapshot-work-quote-arithmetic-correction/seal.json':
            'c7400a6c214ca45c9c169e59238d5788685a88fdae15d1a72217661e222a9a8a',
        'verification/swift-guarded-snapshot-ingress-work/seal.json':
            '75775a7df0048888ab95b40d58831d22e05ea2e3935781904e9a83b57f556561',
        'verification/swift-guarded-snapshot-full-work-independent/seal.json':
            '1a0dfc2f649f9e7196fd64f8a1cf066240c8cdb4acb5fe67cfc5937fd3f9b701',
        'verification/swift-real-profile-loader-binding/seal.json':
            'e1701fb93056b763a06164d7ccf0cae3112f2e27baaa3f4a35aedd8e747665a2',
        'verification/swift-real-profile-loader-independent/seal.json':
            '20841ffd95685e0a65d926c747dfd2c7394341663593cca7c6c01d2c2f329c3f',
        'verification/swift-guarded-snapshot-work-admission/seal.json':
            'e8fe23ee4800a76ac6ca1486604b98b114a1f4dbdec1a25f520641c4e9951940',
        'verification/swift-semantic-adapter-root-review/guarded-snapshot-work-admission-independent-release.json':
            'e902912c64ecb585782fd92e164377e46aefa3c3c1e7771ce0760655c3316e3d',
    }
    checked = []
    for name,digest in expected.items():
        p = ROOT/name
        data = p.read_bytes()
        assert sha(data) == digest, name
        row = dict(path=name, bytes=len(data), sha256=digest)
        if p.name == 'seal.json':
            sealed = json.loads(data)
            total = 0
            for member in sealed['members']:
                item = p.parent/member['path']
                assert item.resolve().is_relative_to(p.parent.resolve())
                raw = item.read_bytes()
                assert (len(raw),sha(raw)) == (member['bytes'],member['sha256']), str(item)
                total += len(raw)
            row.update(members_verified=len(sealed['members']),member_bytes_verified=total)
        if 'work-admission' in name:
            row['status'] = 'released provisional source only; acceptance not inferred'
        checked.append(row)
    named = [
        'verification/swift-guarded-snapshot-owner-storage-closure/host-caller.json',
        'verification/swift-guarded-snapshot-funding-implementation/lifetime-obligations.json',
        'verification/swift-real-profile-loader-binding/accounting.json',
        'verification/swift-real-profile-loader-binding/CONTRACT.md',
        'verification/swift-guarded-snapshot-funding-implementation/source/vm/src/experimental_swift_reactor/control.rs',
        'verification/swift-guarded-snapshot-funding-implementation/source/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs',
        'verification/swift-guarded-snapshot-funding-implementation/source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs',
        'verification/swift-guarded-snapshot-work-admission/work-delta.json',
    ]
    for name in named:
        data = (ROOT/name).read_bytes()
        checked.append(dict(path=name,bytes=len(data),sha256=sha(data)))
    caller = json.loads((ROOT/named[0]).read_text())
    roles = caller['function']['roles']
    assert sum(r['funding_class']=='host-caller' for r in roles)==53
    assert sum(r['funding_class']=='external-harness' for r in roles)==163
    assert caller['enumerated_product_bytes']==81_327
    lifetime = json.loads((ROOT/named[1]).read_text())
    assert len(lifetime['H_pre_ingress']['exact_already_authored_argument_roles'])==7
    loader = json.loads((ROOT/named[2]).read_text())
    assert loader['validation_phase_requested_capacity_maxima']['total_conservative_union']==152_437_784
    result = dict(schema=1,inputs=checked,
                  source144_funding_tree_sha256='7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b',
                  scope='Released seals and explicitly named inputs only; no active sibling review/correction read',
                  provisional_work_admission_accepted=False, host_grant_minted=False,
                  product_or_loader_executed=False)
    (HERE/'input-bindings.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(input_bindings=len(checked),sealed_members_rehashed=sum(x.get('members_verified',0) for x in checked))))


if __name__=='__main__':
    main()
