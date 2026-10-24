#!/usr/bin/env python3
"""Fresh host-only declaration compilation and immutable metadata replay."""
import datetime, hashlib, json, os, pathlib, shutil, subprocess, sys, tarfile
from verify_packet import verify
ROOT=pathlib.Path(__file__).resolve().parents[2]
HERE=pathlib.Path(__file__).resolve().parent
PACKET=pathlib.Path(sys.argv[1]).resolve()
STAMP=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT=HERE/'results'/STAMP; BUILD=HERE/'build'/STAMP
OUT.mkdir(parents=True); BUILD.mkdir(parents=True)
ENV=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'])
ENV.pop('RUSTC_BOOTSTRAP',None)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def manifest(path):return {str(p.relative_to(path)):sha(p) for p in sorted(path.rglob('*')) if p.is_file()}
commands=[];status='failed-independent-review-preflight';summary=None
receipt={}
def run(name,argv,cwd,source=None,target=None):
    before=manifest(source) if source else None
    env=dict(ENV)
    if target:env['CARGO_TARGET_DIR']=str(target)
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    p=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,text=True)
    finish=datetime.datetime.now(datetime.timezone.utc).isoformat()
    for stream in ['stdout','stderr']:(OUT/(name+'.'+stream)).write_text(getattr(p,stream))
    after=manifest(source) if source else None
    commands.append({'name':name,'argv':argv,'cwd':str(cwd),'target':str(target) if target else None,'startedUTC':start,'finishedUTC':finish,'exitCode':p.returncode,'sourceBefore':before,'sourceAfter':after,'sourceTreeSHA256':hashlib.sha256(encoded(before)).hexdigest() if before is not None else None,'stdout':name+'.stdout','stdoutSHA256':sha(OUT/(name+'.stdout')),'stderr':name+'.stderr','stderrSHA256':sha(OUT/(name+'.stderr'))})
    assert p.returncode==0,(name,p.stderr[-3000:])
    assert before==after,name+' changed source'
    print(name,flush=True)
    return p.stdout
try:
    summary=verify(PACKET)
    (OUT/'producer-offline-summary.json').write_bytes(encoded(summary))
    producer=json.loads((PACKET/'receipt.json').read_text())
    for file in ['receipt.json','source-manifest.json','accepted-macro-binding.json','nested-value-component.json','inventory-schema.json']:
        shutil.copyfile(PACKET/file,OUT/('producer-'+file))
    (OUT/'review-inputs').mkdir()
    for name in ['reproduce.py','verify_packet.py','collect_review.py']:
        shutil.copyfile(HERE/name,OUT/'review-inputs'/name)
    run('revision',['git','rev-parse','HEAD'],ROOT)
    run('status',['git','status','--short'],ROOT)
    run('rustc-version',['rustc','--version','--verbose'],ROOT)
    run('cargo-version',['cargo','--version'],ROOT)
    run('python-version',[sys.executable,'--version'],ROOT)
    run('platform',['uname','-a'],ROOT)
    candidate=next(v for v in producer['variants'] if v['label']=='candidate')
    for config,flags in [('swift-debug',['--features','experimental-swift-reactor']),('all-release',['--all-features','--release'])]:
        work=BUILD/config
        with tarfile.open(PACKET/candidate['archive']) as t:t.extractall(work,filter='data')
        source=work/'vm'
        assert manifest(source)==json.loads((PACKET/candidate['manifest']).read_text())
        run('fresh-'+config,['cargo','check','--locked','--offline','--lib',*flags],source,source,BUILD/(config+'-target'))
    (OUT/'binaries').mkdir()
    producer_commands={c['name']:c for c in producer['commands']}
    portable=json.loads((PACKET/'qualifying-artifacts.json').read_text())
    portable_by_id={x['id']:x for x in portable['artifacts']}
    with tarfile.open(PACKET/portable['archive']) as tar:
        portable_data={m.name:tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    binaries=[]
    for layout in producer['layouts']:
        label=layout['label']; command=producer_commands[label+'-run']; original=pathlib.Path(command['argv'][0])
        artifact=portable_by_id[label]
        binary=OUT/'binaries'/label
        binary.write_bytes(portable_data[artifact['archiveMember']]);binary.chmod(0o755)
        assert sha(binary)==layout['binarySHA256']
        output=run('replay-'+label,[str(binary),*command['argv'][1:]],ROOT)
        records=[line[line.index('AF_'):] for line in output.splitlines() if 'AF_' in line]
        assert records==layout['records'],label+' layout replay changed'
        binaries.append({'label':label,'relativePath':str(binary.relative_to(OUT)),'sha256':sha(binary),'records':records})
    receipt['binaries']=binaries
    status='independently-verified-declaration-compiler-layout-only'
finally:
    receipt.update({'schema':'mixer.swift-active-frame-contract-independent-review.v1','status':status,'producerPacket':str(PACKET.relative_to(ROOT)),'producerReceiptSHA256':sha(PACKET/'receipt.json'),'producerOfflineSummary':summary,'commands':commands,'compilerFreshConfigurations':sum(c['name'].startswith('fresh-') and c['exitCode']==0 for c in commands),'requestedFreshConfigurations':2,'metadataReplays':len(receipt.get('binaries',[])),'scope':'Private original-types declaration/lifetime/accounting proposal review only. No guest, frame, native, physical or GA runtime acceptance.','productSourceEdited':False,'guestExecution':False,'frameExecution':False,'nativeRuntime':False,'physicalRuntime':False,'semanticAcceptance':False,'accountingCompletenessAccepted':False,'gaAcceptance':False})
    (OUT/'receipt.json').write_bytes(encoded(receipt))
    print(str(OUT.relative_to(ROOT)),flush=True)
