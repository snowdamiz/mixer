def reconstructed_source():
    candidate=read(CANDIDATE / "copied-source-manifest.json")
    with tarfile.open(CANDIDATE / "isolated-source.tar.gz", "r:gz") as archive:
        members=archive.getmembers()
        assert len(members)==len(candidate)==132 and len({m.name for m in members})==132
        assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
        result={m.name:archive.extractfile(m).read() for m in members}
    assert {n:hashlib.sha256(b).hexdigest() for n,b in result.items()}==candidate
    result['src/experimental_swift_reactor/cache_tests.rs']+=b'\n'+(HERE/'adapter.rs').read_bytes()+b'\n'+(HERE/'adapter-controls.rs').read_bytes()
    result['src/experimental_swift_reactor/lifecycle_tests.rs']+=APPEND.encode()
    return result


def assert_baseline():
    baseline=read(HERE/'baseline-manifest.json')
    assert closure(baseline)==CLOSURE and len(baseline)==132
    reconstructed=reconstructed_source()
    expected={n:hashlib.sha256(b).hexdigest() for n,b in reconstructed.items()}
    assert expected==read(HERE/'copied-build-manifest.json')
    assert source_manifest(SOURCE)==expected
    changed=[n for n in baseline if expected[n]!=baseline[n]]
    assert changed==['src/experimental/cache/borrowed.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/lifecycle_tests.rs']
    return expected


def assert_inputs():
    binding=read(HERE/'binding.json')
    for info in binding['inputs']:
        assert sha(info['path'])==info['sha256'],info['path']
    assert sha(REACTOR)==REACTOR_HASH and REACTOR.stat().st_size==53_777_114
    assert sha(HERE/'harness.rs')==HARNESS_HASH


def prepare():
    assert not (HERE/'binding.json').exists() and not SCRATCH.exists()
    refs={}
    def retain(path,expected=None):
        info=identity(path)
        if expected is not None:assert info['sha256']==expected,str(path)
        refs[info['path']]=info
    authorities=[(CANDIDATE,'seal.json','e4a520641fbad904381bc7438feb0baee4dfca7d716806262da80ac4b20f0305',43),
                 (REVIEW,'seal.json','9f7d6c2357f0464d09932c4632cba543ecf8a20073ea6a3d9f07030de4175ce4',24),
                 (PREVIOUS,'result-seal.json','8f04098c444d63e9d638c32e22297eccdad346222241529ef710c524473e7526',311)]
    verified=[]
    for directory,name,digest,count in authorities:
        retain(directory/name,digest);seal=read(directory/name);assert len(seal['files'])==count
        for n,d in seal['files'].items():retain(directory/n,d)
        for n,d in seal['externalFiles'].items():retain(ROOT/n,d)
        verified.append({'packet':str(directory.relative_to(ROOT)),'sealSHA256':digest,'members':count,'externalMembers':len(seal['externalFiles'])})
    baseline=read(CANDIDATE/'baseline-manifest.json');assert closure(baseline)==CLOSURE
    save('baseline-manifest.json',baseline)
    prior=read(PREVIOUS/'target-once-classification.json')
    f=prior['firstTypedFailure']
    assert (f['resource'],f['attempted'],f['limit'],f['at_failure']['instructions'])==('CacheWork',64000001,64000000,23358291)
    assert prior['initializeCompleted'] and prior['corpus1Attempted'] and not prior['corpus1Completed'] and not prior['corpus2Attempted']
    assert prior['finalCleanupReservationsAndLiveEmpty'] and prior['finalCleanupInvariant'] is None
    context=[]
    for n in ('AGENTS.md','PLAN.md','STATUS.md','mixer-product-plan.md'):
        out=HERE/'context'/n;out.parent.mkdir(exist_ok=True);shutil.copyfile(ROOT/n,out)
        retain(out);context.append({'originalPath':str(ROOT/n),'snapshot':str(out.relative_to(HERE)),'sha256':sha(out),'authority':'archived context observation only; mutable live index not sealed'})
    oracle=QUALIFIED/'evidence/2026-10-23-qualified/native-command-run.stdout'
    retain(oracle);native=strict_json(oracle.read_text())
    assert set(native)==set(EXPECTED) and len(native)==11
    assert all(type(native[k]) is type(EXPECTED[k]) and native[k]==EXPECTED[k] for k in EXPECTED)
    retain(REACTOR,REACTOR_HASH)
    assert REACTOR.stat().st_size==53_777_114
    SCRATCH.mkdir(mode=0o700);(SCRATCH/'tmp').mkdir(mode=0o700)
    source=reconstructed_source()
    for n,b in source.items():
        out=SOURCE/n;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
    modified={n:hashlib.sha256(b).hexdigest() for n,b in source.items()}
    save('copied-build-manifest.json',modified)
    assert_baseline()
    save('source-audit.json',{'baselineClosure':CLOSURE,'candidateSourceManifestSHA256':sha(CANDIDATE/'copied-source-manifest.json'),
        'sourceFiles':132,'deltaFromAcceptedObserver':['src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/lifecycle_tests.rs'],
        'remainingCandidateFilesByteIdentical':130,'originalHarnessSHA256':sha(PREVIOUS/'harness.rs'),'harnessSHA256':sha(HERE/'harness.rs'),
        'liveVmQueried':False,'gitQueried':False,'sealedAuthorities':verified})
    save('binding.json',{'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'baselineClosure':CLOSURE,'sourceRevisionContext':'6b8aba350224ed19f678669bdbea6b359d8de68b',
        'sourceRevisionMeaning':'root supplied context; exact sealed source content authoritative; no Git or live VM query',
        'inputs':list(refs.values()),'contractSnapshots':context,'target':identity(REACTOR),'expectedObservation':EXPECTED,
        'acceptedObserver':identity(CANDIDATE/'seal.json'),'acceptedIndependentReview':identity(REVIEW/'seal.json'),
        'historicalFailurePacket':identity(PREVIOUS/'result-seal.json'),'historicalFailure':f,
        'selectedPhases':['complete validation','adoption','construct original owner','Initialize35','Corpus62','Corpus62','consuming cleanup'],
        'targetExecutionSelectedByRoot':False,'productionBaselineModifiedByDiagnostic':False,'hostDiagnosticOnly':True,
        'historicalNativeAndCompilerOnlyDataReferences':True,'nativePhysicalOrEmulatorRun':False,
        'compilerTools':tools()})
    assert_inputs()
    print(json.dumps({'prepared':True,'files':132,'baselineClosure':CLOSURE,'instrumentedManifestSHA256':sha(HERE/'copied-build-manifest.json'),'targetExecuted':False}))
