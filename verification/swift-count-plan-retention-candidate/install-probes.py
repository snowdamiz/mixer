#!/usr/bin/env python3
import pathlib,sys
out=pathlib.Path(__file__).resolve().parent;root=out.parents[1]
for mode in sys.argv[1:]:
    base=out/'.scratch'/mode
    for target,source in [('src/experimental/cache/tests.rs','generic-probes.rs'),('src/experimental_swift_reactor/cache.rs','inspection.rs'),('src/experimental_swift_reactor/cache_tests.rs','swift-probes.rs')]:
        p=base/target;s=p.read_text();extra=(out/source).read_text();assert extra not in s
        if source=='swift-probes.rs':
            s=s.replace('    elision_observe_checkpoint(control);','    elision_observe_checkpoint(control);\n    count_candidate_checkpoint(control);',1)
            s+='\n'+(root/'verification/swift-cost-retention-candidate/common-tests.rs').read_text()
            s+='\nconst COUNT_POLICY: bool = '+str(mode=='candidate').lower()+';\n'
        if source=='generic-probes.rs' and mode=='candidate':
            extra=extra.replace('size_of::<decode::Counts>()','size_of::<<FrozenMode as CacheMode>::ScanOutcome>()')
            extra=extra.replace('size_of::<Result<decode::Counts,CacheFailure>>()','size_of::<Result<<FrozenMode as CacheMode>::ScanOutcome,CacheFailure>>()')
        p.write_text(s+'\n'+extra)
    if mode=='candidate':
        p=base/'src/experimental_swift_reactor/cache.rs';p.write_text(p.read_text()+'\n'+(out/'inventory-probe.rs').read_text())
print('Installed identical probes plus per-mode expected cold priority')
