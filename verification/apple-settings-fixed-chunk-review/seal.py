#!/usr/bin/env python3
"""Seal the independent decision after all scoped evidence and cleanup checks."""
import datetime,hashlib,json,pathlib,stat,tarfile
B=pathlib.Path(__file__).resolve().parent;ROOT=B.parents[1]
P=ROOT/'verification/apple-settings-fixed-chunk-implementation'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def save(name,data):(B/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
def load(name):return json.loads((B/name).read_bytes())
def main():
    a=load('audit.json');r=load('receiver-controls.json');f=load('foundation-controls.json');t=load('typecheck.json');c=load('cleanup.json')
    assert a['passed'] and r['passed'] and r['methods']==7 and len(r['controls'])==99
    assert f['passed'] and f['foundationEnvelopeRows']==96 and len(f['controls'])==26 and f['body8192Accepted8193Rejected']
    assert t['passed'] and c['ownedScratchAbsent']
    assert not any((B/name).exists() for name in ['owned-host','owned-typecheck','synthetic-attempts'])
    assert sha((P/'handoff.json').read_bytes())==a['producerHandoffSHA256']
    producer=json.loads((P/'handoff.json').read_bytes())
    for name,row in producer['members'].items():
        path=ROOT/name;assert stat.S_ISREG(path.lstat().st_mode) and sha(path.read_bytes())==row['sha256'] and path.stat().st_size==row['bytes'],name
    manifest=load('synthetic-evidence-manifest.json')
    with tarfile.open(B/'independent-synthetic-evidence.tar.gz') as tf:
        assert len(tf.getmembers())==len(manifest)+1
        for member in tf.getmembers():
            assert not pathlib.PurePosixPath(member.name).is_absolute() and '..' not in pathlib.PurePosixPath(member.name).parts
            if member.name=='synthetic-attempts':assert member.isdir();continue
            row=manifest[member.name]
            assert row['kind']==('file' if member.isfile() or member.islnk() else 'directory' if member.isdir() else 'symlink')
            if member.isfile() or member.islnk():
                target=member;seen=set()
                while target.islnk():
                    name=pathlib.PurePosixPath(target.linkname)
                    assert not name.is_absolute() and '..' not in name.parts and target.linkname in manifest
                    assert target.linkname not in seen
                    seen.add(target.linkname);target=tf.getmember(target.linkname)
                assert target.isfile()
                raw=tf.extractfile(target).read();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
            if member.issym():assert member.linkname==row['target']
    scripts={n:sha((B/n).read_bytes()) for n in ['audit.py','controls.py','run.py','fixtures.py','generate_probe.py','probe_tail.swift','independent-probe.swift','frozen-receiver.py']}
    sources={str(p.relative_to(B/'sources')):sha(p.read_bytes()) for p in sorted((B/'sources').rglob('*')) if p.is_file()}
    save('execution-source-bindings.json',dict(executedControlSources=scripts,exactReviewedSources=sources,exactSourceTreeSHA256=sha(json.dumps(sources,sort_keys=True,separators=(',',':')).encode()),producerSourceBindingsSHA256=a['sourceBindingsSHA256']))
    commands={str(p.relative_to(B)):json.loads(p.read_bytes()) for p in sorted((B/'commands').glob('*.json'))}
    assert all(row['ownedGroupEmpty'] and row['stdoutEOF'] and row['stderrEOF'] and not row['timedOut'] for row in commands.values())
    assert all(row['exitCode']==0 for row in commands.values())
    failed=load('attempt-1-foundation/commands/foundation-compile.json')
    assert failed['exitCode']==1 and failed['ownedGroupEmpty'] and not failed['timedOut']
    save('exploration-errors.json',{'scope':'review harness/exploration errors; no product or native execution','items':[{'command':'sed -n 1,260p verification/apple-settings-fixed-chunk-implementation/test_controls.py','exitCode':1,'reason':'nonexistent speculative test filename; inspected actual test_fixed_chunk.py next'},{'command':'rg typecheck in narrow initial instrumentation paths','exitCode':1,'reason':'no matching standalone evidence; controller supplied accepted typecheck-2 receipt'},{'command':'json.loads(commands/foundation-execute.stdout)','exitCode':1,'reason':'initial successful probe stdout began with the retained mark log; final probe now writes a separate JSON report'},{'command':'seal.py then verify.py','exitCode':1,'reason':'first verifier did not classify confined archive hardlinks as regular filesystem members; failure retained in attempt-1-seal, verifier repaired with lexical confinement and regular-target checks; following verify failed because seal emitted no handoff'}]})
    decision=dict(schema=1,status='ACCEPTED_SCOPED',findings=[],acceptedScope=['isolated exact fixed4992 derivative source','independent synthetic receiver/Foundation host consistency','complete exact four-source UIKit/XCTest simulator-target typecheck'],producerHandoffSHA256=a['producerHandoffSHA256'],producerSourceArchiveSHA256=producer['sourceReviewArchiveSHA256'],rootSelectionSHA256='99edd321744935dc9c6c1c3ccebe28706759e270100b72319f58a0338fee73e7',genericRunnerBuildRequiresSeparateRootSelection=True,nativeRuntimeRequiresSeparateRootSelection=True,nativeAccepted=False,gaAccepted=False,originalSettingsFailed=True,dependentTabSkipped=True,physicalPhones='disconnected-deferred')
    save('review.json',decision)
    receipt=dict(schema=1,observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS_SCOPED',accountableReviewer='independent apple_settings_fixed_chunk_review agent',controllerSuppliedRootRevision='be472ce6424a691de5673e3438d2768264827d23',producerSourceRevisionLabel=a['sourceRevisionLabel'],producerMembersVerified=176,sourceMembers=72,changedEndpoints=2,unchangedSources=70,receiverMethods=r['methods'],receiverDetailedControls=len(r['controls']),foundationClientControls=len(f['controls']),foundationEnvelopeRows=f['foundationEnvelopeRows'],maximumObservedFoundationBody=f['maximumFiniteEnvelopeBody'],closedMetadataBytes=f['closedMetadataBytesExcludingUptimeAndData'],binary64FormattingExhaustive=False,bodyGuard8192Accepted8193Rejected=True,fullUIKitXCTestTypecheck=True,nativeProductBuild=False,nativeRuntime=False,listener=False,network=False,deviceQueries=False,ui=False,screenCapture=False,gitOperations=False,producerUnchangedAfterTests=True,allOwnedWorkingScratchAbsent=True,allFinalCommandsExitZeroEOFAndGroupsEmpty=True,retainedReviewHarnessCompilerFailures=1,failedCompilerInvocationReaped=True,syntheticArchiveSHA256=c['archiveSHA256'],testDataConstructorShared=True,independentAssertionsAndFaults=True,producerTestSuiteRerun=False,nativeAccepted=False,gaAccepted=False,originalV6=dict(settings='failed',tab='skipped',xcodeExitCode=65,strictImporter='rejected'),physicalPhones='disconnected-deferred',limitations=['No HTTP/framing/capability/asynchronous networking or native provenance proof from adapters.','Finite Foundation rows are not exhaustive binary64 formatting proof.','Typechecking does not establish a native runner build, execution or acceptance.','New execution requires coordinated root source/product/importer binding; originals remain historical.','Physical-phone matrix, external immutable FieldLog, signing/store/operational/GA gates remain pending.'])
    save('receipt.json',receipt)
    rows={}
    paths=[ROOT/'docs/apple-settings-fixed-chunk-review.md']+[p for p in sorted(B.rglob('*')) if p.is_file() and p.name not in ['handoff.json','handoff.sha256','verification-result.json']]
    for p in paths:
        assert stat.S_ISREG(p.lstat().st_mode)
        raw=p.read_bytes();rows[str(p.relative_to(ROOT))]=dict(bytes=len(raw),sha256=sha(raw))
    save('handoff.json',dict(schema=1,scope='independent fixed4992 source/host review and full UIKit-XCTest typecheck only',members=rows,decisionSHA256=sha((B/'review.json').read_bytes()),producerHandoffSHA256=a['producerHandoffSHA256'],nativeAccepted=False,gaAccepted=False))
    (B/'handoff.sha256').write_text(sha((B/'handoff.json').read_bytes())+'\n')
    print(json.dumps(dict(sealed=True,members=len(rows),handoffSHA256=sha((B/'handoff.json').read_bytes()))))
if __name__=='__main__':main()
