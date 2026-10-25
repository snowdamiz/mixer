#!/usr/bin/env python3
"""Construct this lane's driver/harness from the sealed prior driver as data only."""
from pathlib import Path
import difflib,hashlib,json
H=Path(__file__).resolve().parent;P=H.parent/'swift-exact-reactor-after-plan-reuse'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original=(P/'harness.rs').read_text()
assert sha(P/'harness.rs')=='d72da7bc7aaf4e31b7093fde497f357226d3a4dd954eb577909209102a0bfb00'
s=original
s=s.replace('    use std::io::Write;','    use std::io::Write;\n    use crate::experimental_swift_reactor::cache_tests::{full_attribution_begin, full_attribution_snapshot, FullAttributionPhase};')
old='            quote(&hex(wasi.stderr())), owner.cache.as_ref().unwrap().usage().json()));\n'
new=old+'''        let label=match event {
            "constructed"=>FullAttributionPhase::Constructed,"initialize"=>FullAttributionPhase::Initialize,
            "corpus_1"=>FullAttributionPhase::Corpus1,"corpus_2"=>FullAttributionPhase::Corpus2,
            "before_cleanup"=>FullAttributionPhase::BeforeCleanup,_=>return,
        };
        if let (Some(control),Some(cache))=(owner.control.as_ref(),owner.cache.as_ref()) {
            full_attribution_snapshot(label,control.usage(None).cache_work,cache.usage().decodes,false);
        }
'''
assert s.count(old)==1;s=s.replace(old,new)
old='        snapshot("before_cleanup", &owner);\n';new=old+'        let full_final_decodes=owner.cache.as_ref().map(|cache|cache.usage().decodes);\n'
assert s.count(old)==1;s=s.replace(old,new)
old='        tail.complete((owned, returned), &mut failure, &mut usage);\n        emit("final_failure", failure.json());\n        emit("final_cleanup_usage", usage.json());\n';new=old+'''        if let (Some(u),Some(decodes))=(usage,full_final_decodes) {
            full_attribution_snapshot(FullAttributionPhase::FinalCleanup,u.cache_work,decodes,true);
        }
'''
assert s.count(old)==1;s=s.replace(old,new)
old='        let mut returned = Some(SwiftReactorInstance::construct';new='        full_attribution_begin(); // Exactly once, before this original cache/control construction.\n'+old
assert s.count(old)==1;s=s.replace(old,new)
old='                emit("final_cleanup_usage", control.finish_owned_cleanup(None).json());';new='''                let full_final_usage=control.finish_owned_cleanup(None);
                emit("final_cleanup_usage", full_final_usage.json());
                full_attribution_snapshot(FullAttributionPhase::FinalCleanup,full_final_usage.cache_work,0,true);'''
assert s.count(old)==1;s=s.replace(old,new)
old='                emit("final_cleanup_usage", usage.json());\n';new=old+'''                if let Some(u)=usage {full_attribution_snapshot(FullAttributionPhase::FinalCleanup,u.cache_work,0,true);}
'''
assert s.count(old)==1;s=s.replace(old,new)
(H/'harness.rs').write_text(s)
(H/'harness-changes.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='historical/harness.rs',tofile='prepared/harness.rs')))
# Copy source text, never import or execute the historical driver.
s=(P/'diagnostic.py').read_text();original_driver=s
s=s.replace('import argparse\n','import argparse\nimport tarfile\nimport telemetry\n')
s=s.replace('CARGO_NET_OFFLINE="true", CARGO_TARGET_DIR=str(TARGET),','CARGO_NET_OFFLINE="true", CARGO_BUILD_JOBS="2", CARGO_TARGET_DIR=str(TARGET),')
s=s.replace('"""One bounded after-plan-reuse exact Swift reactor diagnostic; no live VM writes."""','"""Fresh test-only current-attribution preparation; real target requires root selection."""')
s=s.replace('BASELINE = HERE / "baseline"','CANDIDATE = HERE.parent / "swift-cache-current-attribution-observer"\nREVIEW = HERE.parent / "swift-cache-attribution-independent-review"\nPREVIOUS = HERE.parent / "swift-exact-reactor-after-plan-reuse"')
s=s.replace('HARNESS_HASH = "d72da7bc7aaf4e31b7093fde497f357226d3a4dd954eb577909209102a0bfb00"','HARNESS_HASH = '+repr(sha(H/'harness.rs')))
start=s.index('def assert_baseline():');end=s.index('\n\ndef observe_group(',start)
s=s[:start]+(H/'preparation-functions.py').read_text().rstrip()+s[end:]
# Keep original build/test-list flow; add only the separate finite adapter controls.
s=s.replace('    save(name + "-result.json", result)\n','    save(name + "-result.json", result)\n    save(name + "-telemetry.json", telemetry.classify(stdout, observed))\n')
old='    commands = ["build-001", "list-001", "control-001", "control-002", "driver-observation-controls"]'
new='    commands = ["build-001", "list-001", "control-001", "control-002", "adapter-controls", "driver-observation-controls"]'
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace('"byte-identical selected harness and accepted baseline"','"unchanged original workload/authority/limits/cleanup; accepted observer plus passive test-only adapter"')
s=s.replace('    files = ["baseline-manifest.json",','    files = ["adapter.rs", "adapter-controls.rs", "telemetry.py", "output-contract.json", "baseline-manifest.json",')
s=s.replace('"proposed-command.json", "driver-changes.diff",','"proposed-command.json", "driver-changes.diff",')
# Existing root selection guard and O_EXCL one-attempt marker stay literal.
old='        assert selection["maxTargetAttempts"] == 1\n'
new=old+'        assert selection["sourceManifestSHA256"] == sha(HERE / "copied-build-manifest.json")\n        assert selection["telemetryClassifierSHA256"] == sha(HERE / "telemetry.py")\n        assert selection["outputContractSHA256"] == sha(HERE / "output-contract.json")\n'
assert s.count(old)==1;s=s.replace(old,new)
# Source-only archived fallback supports review after owned build cleanup; restoration
# is separate and must re-create this exact manifest before root dispatch.
start=s.index('\n\ndef cleanup():');end=s.index('\n\n\ndef host_controls():',start)
s=s[:start]+(H/'cleanup-functions.py').read_text().rstrip()+s[end:]
extra='''\n\ndef adapter_controls():
    binary=read(HERE / "binary.json")
    assert identity(BINARY)==binary["retained"]
    argv=[str(BINARY),"experimental_swift_reactor::cache_tests::full_attribution_adapter_","--nocapture","--test-threads=1"]
    receipt,stdout,_=record_command("adapter-controls",argv,60)
    assert receipt["passed"]
    assert "3 passed; 0 failed; 0 ignored" in stdout.read_text()
    print(json.dumps({"adapterControlsPassed":3,"targetExecuted":False}))
    return 0
'''
s=s.replace('\n\ndef main():',extra+'\n\ndef main():')
s=s.replace('"host-controls", "propose", "target", "cleanup"','"host-controls", "adapter-controls", "propose", "target", "cleanup"')
s=s.replace('"host-controls": host_controls, "propose": propose,','"host-controls": host_controls, "adapter-controls": adapter_controls, "propose": propose,')
(H/'diagnostic.py').write_text(s)
(H/'driver-changes.diff').write_text(''.join(difflib.unified_diff(original_driver.splitlines(True),s.splitlines(True),fromfile='historical/diagnostic.py',tofile='prepared/diagnostic.py')))
(H/'test_driver.py').write_bytes((P/'test_driver.py').read_bytes().replace(b'if __name__ == "__main__":', (H/'telemetry-controls.py').read_bytes()+b'\nif __name__ == "__main__":'))
print(json.dumps({'harnessSHA256':sha(H/'harness.rs'),'driverSHA256':sha(H/'diagnostic.py'),'historicalHarnessSHA256':sha(P/'harness.rs')}))
