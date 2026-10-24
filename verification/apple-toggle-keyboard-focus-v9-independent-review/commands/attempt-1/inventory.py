"""Independently verify selected seals and bind actual loaded source/endpoint."""
import hashlib
import inspect
import json
import pathlib
import sys
import types

import independent_flow as f
import durable_settings as d

HERE=f.HERE; ROOT=f.ROOT
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())


def run():
    selected={
        'verification/apple-toggle-keyboard-focus-v9-preparation/packet-seal.json':'a9f7f3843bd8cfbd2f751f70d2a0b02e503166129ab98637d3602bba2eb4c0f5',
        'verification/apple-toggle-keyboard-focus-v8-root-review/v9-commit-point-selection.json':'cb3fe08781f93cae77c143676544c25c178e751146c8f45043d21875309da795'}
    for name,expected in selected.items():
        assert sha(ROOT/name)==expected,name
    seal=read(f.PRODUCER/'packet-seal.json')
    inputs={**read(f.PRODUCER/'input-bindings.json'),**seal['files'],**selected}
    links=[]
    for name,expected in inputs.items():
        path=pathlib.Path(name) if name.startswith('/') else ROOT/name
        assert path.is_file() and sha(path)==expected,name
        if path.is_symlink():
            links.append(dict(path=str(path),target=str(path.readlink()),resolved=str(path.resolve()),sha256=expected))
    copies=read(f.PRODUCER/'immutable-reuse.json')['exactCopies']
    for name,source in copies.items():
        assert sha(ROOT/name)==sha(ROOT/source),name
    modules={}
    queue=[f.p,f.p.runtime,f.p.h,f.replay,f.t,d,*list(sys.modules.values())]
    seen=set()
    while queue:
        module=queue.pop()
        if not isinstance(module,types.ModuleType) or id(module) in seen:
            continue
        seen.add(id(module)); path=getattr(module,'__file__',None)
        if not path:
            continue
        path=pathlib.Path(path).resolve()
        if not path.is_relative_to(ROOT):
            continue
        modules[str(path.relative_to(ROOT))]=sha(path)
        queue.extend(x for x in vars(module).values() if isinstance(x,types.ModuleType))
    for name,value in modules.items():
        if not name.startswith(str(HERE.relative_to(ROOT))+'/'):
            assert inputs.get(name)==value,('Unbound loaded producer/imported source',name)
    def definition(value):
        path=pathlib.Path(inspect.getsourcefile(value)).resolve()
        return dict(qualifiedName=value.__qualname__,path=str(path.relative_to(ROOT)),
                    line=inspect.getsourcelines(value)[1],sha256=sha(path))
    relationship={
        'runner':definition(f.p.main),
        'bridgeMRO':[dict(qualifiedName=x.__qualname__,module=x.__module__) for x in f.p.h.Bridge.__mro__],
        'bridgeRequest':definition(f.p.h.Bridge.request),
        'bridgeInternalRequest':definition(f.p.h.Bridge._request),
        'sessionRequest':definition(f.t.Session.request),
        'transactionCommit':definition(d.TransactionStore.commit),
        'retirement':definition(d.TransactionStore.resolve_retirement),
        'httpServerFactory':definition(f.p.h.server_for),
        'summaryWriter':definition(f.p.h.Bridge.persist_summary),
        'replay':definition(f.replay.replay)}
    assert relationship['httpServerFactory']['path']=='verification/apple-toggle-pan-origin-correction/bridge.py'
    assert relationship['bridgeRequest']['path']==str((f.PRODUCER/'settings_telemetry.py').relative_to(ROOT))
    assert f.t.__file__==str(f.PRODUCER/'settings_telemetry.py')
    assert d.__file__==str(f.PRODUCER/'durable_settings.py')
    value=dict(selectedPins=selected,allInputHashesVerified=True,inputFileCount=len(inputs),
               producerSealFileCount=len(seal['files']),immutableCopiesVerified=len(copies),
               loadedSourceFiles=modules,sourceAndEndpointRelationship=relationship,
               sourceRevisionContext=seal['sourceRevisionContext'],
               candidateSourceClosureSHA256=seal['candidateSourceClosureSHA256'],
               candidateArchiveSHA256=seal['candidateArchiveSHA256'],
               testRunnerSourceTreeSHA256=seal['testRunnerSourceTreeSHA256'],
               testRunnerProductTreeSHA256=seal['testRunnerProductTreeSHA256'],
               testRunnerArchiveSHA256=seal['testRunnerArchiveSHA256'],
               producerResultsReusedAsSealedEvidence=dict(sessionMethods=seal['actualSessionMethods'],
                   persistenceMethods=seal['actualPersistenceMethods'],httpControls=seal['concretePersistenceHTTPControls'],
                   swiftResolverControls=seal['unchangedSwiftResolverControls'],transportControls=seal['unchangedTransportControls']),
               nativeExecuted=False,nativeInstancesQueried=False,sourceOnlyNoCompilation=True)
    (HERE/'review-inputs.json').write_text(json.dumps(inputs,sort_keys=True,indent=2)+'\n')
    (HERE/'tool-link-bindings.json').write_text(json.dumps(links,sort_keys=True,indent=2)+'\n')
    (HERE/'inventory.json').write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(inputFileCount=len(inputs),immutableCopiesVerified=len(copies),loadedSourceFiles=len(modules),pinsVerified=True)))


if __name__=='__main__':run()
