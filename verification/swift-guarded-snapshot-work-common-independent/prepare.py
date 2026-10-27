"""Frozen-original custody and independent arithmetic preparation only.

This script deliberately never opens the active common-correction directory.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json
import platform
import sys

HERE = Path(__file__).resolve().parent
VERIFICATION = HERE.parent
ORIGINAL = VERIFICATION / "swift-guarded-snapshot-work-admission"
INDEPENDENT = VERIFICATION / "swift-guarded-snapshot-work-admission-independent"
BASE = VERIFICATION / "swift-guarded-snapshot-funding-implementation"
CONTROL = "src/experimental_swift_reactor/control.rs"
TESTS = "src/experimental_swift_reactor/control_tests.rs"
EXPECTED_ORIGINAL = "e8fe23ee4800a76ac6ca1486604b98b114a1f4dbdec1a25f520641c4e9951940"
EXPECTED_INDEPENDENT = "68619807028aec0ac511a287ebcc33f9788e22860b0e39bb0fc6daee0620956a"
EXPECTED_FINDING = "6664555f320e78995c8e0eed9766308bfc43240bfd0cbf21bf0c1ab8db05b894"
EXPECTED_TREE = "c909e78b0cd12c719f8366f5a701e871c86d8d640d90f34cb5dbe49ea9d5e712"
def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value,sort_keys=True,separators=(",", ":")).encode()
def load(path): return json.loads(path.read_text())
def write(name, value): (HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
def member(path, relative):
    data=path.read_bytes()
    return dict(path=relative,bytes=len(data),sha256=sha(data))
def verify_seal(directory, expected, count, total):
    data=(directory/"seal.json").read_bytes(); assert sha(data)==expected
    seal=json.loads(data)
    assert len(seal["members"])==count
    assert sum(row["bytes"] for row in seal["members"])==total
    assert sha(canonical(seal["members"]))==seal["manifest_sha256"]
    for row in seal["members"]: assert member(directory/row["path"],row["path"])==row,row["path"]
    return dict(seal_sha256=expected,members=count,bytes=total)
def custody():
    original=verify_seal(ORIGINAL,EXPECTED_ORIGINAL,85,5584323)
    independent=verify_seal(INDEPENDENT,EXPECTED_INDEPENDENT,50,3647938)
    finding=VERIFICATION/"swift-semantic-adapter-root-review/guarded-snapshot-work-admission-review-finding.json"
    assert sha(finding.read_bytes())==EXPECTED_FINDING
    manifest=load(ORIGINAL/"source-manifest.json")
    assert sha((BASE/"seal.json").read_bytes())==manifest["base_seal_sha256"]
    rows=[]
    for row in manifest["members"]:
        path=ORIGINAL/"overlay"/row["path"]
        if not path.exists(): path=BASE/"source/vm"/row["path"]
        assert member(path,row["path"])==row,row["path"]
        rows.append(row)
    assert len(rows)==144 and sha(canonical(rows))==EXPECTED_TREE==manifest["source_tree_sha256"]
    return dict(original=original,independent=independent,root_finding_sha256=EXPECTED_FINDING,
        source_members=144,original_source_tree_sha256=EXPECTED_TREE)
def checked_add(a,b,maximum): return a+b if a<=maximum-b else None
def fold(f0,terms,maximum):
    value=f0
    for term in terms:
        value=checked_add(value,term,maximum) if value is not None else None
    return value
def arithmetic():
    passed=Counter(); C=78240; D=1436; S=941467; H=81327; A=430175
    for width in [32,64]:
        maximum=(1<<width)-1
        points={0,1,366312,366896,maximum}
        for total in [C,C+D,C+S+D,C+S+D+H,C+S+D+A,C+S+D+H+A]:
            for offset in [-1,0,1]: points.add(maximum-total+offset)
        for f0 in sorted(points):
            if not 0<=f0<=maximum: continue
            old_common=fold(f0,[C],maximum); new_common=fold(f0,[C,D],maximum)
            assert new_common==fold(f0,[C+D],maximum);passed["common_checked_recipe"]+=1
            if new_common is not None:
                assert old_common is not None and new_common-old_common==D
                passed["common_increment"]+=1
            elif old_common is not None:
                assert maximum-D < old_common<=maximum
                passed["common_new_overflow_fails_closed"]+=1
            for suffix in [[],[H],[A],[H,A]]:
                old=fold(f0,[C,S,D]+suffix,maximum)
                new=fold(f0,[C,D,S]+suffix,maximum)
                assert old==new;passed["selected_admitted_checked_equivalence"]+=1
        for f0,expected in [(366312,(445988,1387455,1817630)),(366896,(446572,1388039,1818214))]:
            assert (fold(f0,[C,D],maximum),fold(f0,[C,D,S],maximum),fold(f0,[C,D,S,A],maximum))==expected
            passed["production_unit_base_floors"]+=1
        assert fold(366896,[C,D,S,H],maximum)==1469366
        assert fold(366896,[C,D,S,H,A],maximum)==1899541
        passed["unit_H_floors"]+=2
    return dict(checks_passed=sum(passed.values()),groups=dict(passed),
        widths=[32,64],scope="independent checked nonnegative-integer model; no runtime authorization")
def main():
    assert not (HERE/"seal.json").exists()
    inputs=custody(); model=arithmetic()
    source=(ORIGINAL/"overlay"/CONTROL).read_bytes()
    start=source.index(b"// Exact logical source-place recipe")
    end=source.index(b"#[cfg(not(test))]\nconst SNAPSHOT_SCOPE_FOUNDATION",start)
    binding=dict(control_sha256=sha(source),const_region_sha256=sha(source[start:end]),
        pre_const_sha256=sha(source[:start]),post_const_sha256=sha(source[end:]),
        runtime_body_bytes=len(source)-end,original_controls_sha256=sha((BASE/"source/vm"/TESTS).read_bytes()),
        scope="all bytes outside bounded const-attribution region must match correction exactly")
    write("preparation.json",dict(schema=1,command="python3 verification/swift-guarded-snapshot-work-common-independent/prepare.py",
        python=sys.version,platform=platform.platform(),inputs=inputs,arithmetic=model,
        original_runtime_binding=binding,correction_read=False,stage="awaiting explicit root release"))
    print(json.dumps(dict(inputs=inputs,arithmetic=model,correction_read=False),sort_keys=True))
if __name__=="__main__": main()
