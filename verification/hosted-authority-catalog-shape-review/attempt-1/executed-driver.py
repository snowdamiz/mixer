#!/usr/bin/env python3
"""Independent raw-shape review: frozen-input replay and one owned PG cluster."""
import argparse, datetime, gzip, hashlib, json, os, pathlib, platform, shutil, subprocess, sys, tempfile, time, traceback
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PRODUCER=ROOT/'verification/hosted-authority-catalog-shape-correction'
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args();out=pathlib.Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(__file__,out/'executed-driver.py')
    shutil.copytree(PRODUCER/'candidate',out/'candidate')
    inputs=['receipt.json','artifact-manifest.json','check.py','boundary-tests.py','raw-field-domains.json','selected-expected.json','delta-manifest.json','implementation.diff','independent-runtime.py',
            'inputs/verification/hosted-authority-catalog-review/attempt-2/domain-probes.json',
            'inputs/verification/hosted-authority-catalog-review/attempt-2/independent/observations/001.json.gz']
    inputs += [str(p.relative_to(PRODUCER)) for p in (PRODUCER/'platform-catalog-types').rglob('*') if p.is_file()]
    bindings=[]
    for rel in inputs:
        p=PRODUCER/rel;q=out/'inputs'/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
        bindings.append({'path':str(p.relative_to(ROOT)),'copy':str(q.relative_to(out)),'bytes':q.stat().st_size,'sha256':sha(q.read_bytes())})
    (out/'input-manifest.json').write_text(json.dumps(bindings,indent=2)+'\n')
    source=[{'path':str(p.relative_to(out/'candidate')),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted((out/'candidate').rglob('*')) if p.is_file()]
    (out/'source-manifest.json').write_text(json.dumps(source,indent=2)+'\n')
    assert sha(canonical(source).encode())=='7e2a24ec2aad45d07d2dd8a5d581fa8df5966e841981d20b27c75acd1de74b40'
    assert sha((PRODUCER/'receipt.json').read_bytes())=='49ecbed394b965f68f50e242da0103005d3e86fee23a42955fc5530b982f2e22'
    assert sha((out/'inputs/selected-expected.json').read_bytes())=='78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e'
    commands=[];receipt={'schema':1,'started_utc':utc(),'source_digest':sha(canonical(source).encode()),'producer_receipt_sha256':sha((PRODUCER/'receipt.json').read_bytes()),'success':False}
    def run(argv,env=None,timeout=60,check=True):
        rec={'argv':list(map(str,argv)),'cwd':str(ROOT),'started_utc':utc(),'timeout_seconds':timeout};t=time.monotonic()
        if env:rec['environment_overrides']={k:v for k,v in env.items() if k.startswith('MIXER_') or k=='PYTHONDONTWRITEBYTECODE'}
        try:
            p=subprocess.run(rec['argv'],cwd=ROOT,capture_output=True,text=True,env=env,timeout=timeout);rec.update(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,stdout_sha256=sha(p.stdout.encode()),stderr_sha256=sha(p.stderr.encode()))
        except Exception as exc:rec['error']=repr(exc);raise
        finally:rec['seconds']=time.monotonic()-t;commands.append(rec);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        if check and p.returncode:raise RuntimeError(rec)
        return p
    scratch=None;data=None;started=False;ok=False
    try:
        receipt['head']=run(['git','rev-parse','HEAD']).stdout.strip();receipt['tree']=run(['git','rev-parse','HEAD^{tree}']).stdout.strip();receipt['platform']=platform.platform()
        receipt['tools']={a[0]:run(a).stdout.strip() for a in [['python3','--version'],['postgres','--version'],['pg_ctl','--version'],['psql','--version'],['pg_config','--libdir']]}
        lib=pathlib.Path(receipt['tools']['pg_config'])/'libpq.5.dylib';receipt['libpq']={'path':str(lib.resolve()),'sha256':sha(lib.read_bytes())}
        integrity=run(['python3','-B',PRODUCER/'check.py']);receipt['producer_check']=json.loads(integrity.stdout);assert receipt['producer_check']['bindings']==277
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',MIXER_SHAPE_PACKET=str(out/'inputs'))
        # The frozen boundary script expects candidate alongside its packet inputs.
        shutil.copytree(out/'candidate',out/'inputs/candidate')
        shutil.copytree(out/'inputs/inputs',out/'inputs/inputs',dirs_exist_ok=True) if False else None
        run(['python3','-B',out/'inputs/boundary-tests.py','--out',out/'model-replay'],env=env)
        shutil.copyfile(HERE/'extra-probes.py',out/'executed-extra-probes.py')
        run(['python3','-B',out/'executed-extra-probes.py','--packet',out,'--out',out/'extra-models.json'])
        # One owned, socket-only cluster. Other projects and native tools are untouched.
        scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-catalog-shape-review-',dir='/private/tmp')).resolve();data=scratch/'pg';sock=scratch/'socket';sock.mkdir(mode=0o700);receipt['scratch']=str(scratch)
        run(['initdb','-D',data,'-A','trust','--no-locale','--encoding=UTF8'])
        run(['pg_ctl','-D',data,'-l',scratch/'postgres.log','-o',f"-F -k {sock} -c listen_addresses='' -c unix_socket_permissions=0700",'-w','start']);started=True
        run(['createdb','-h',sock,'authority_contract'])
        padding='CREATE SCHEMA shape_review_padding;'+''.join(f'CREATE TABLE shape_review_padding.p{i}(a integer);' for i in range(89))
        run(['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-c',padding])
        run(['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-f',out/'candidate/frozen/schema.sql'])
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',MIXER_AUTHZ_SOCKET=str(sock),MIXER_AUTHZ_OUT=str(out/'runtime'),MIXER_AUTHZ_EXPECTED=str(out/'inputs/selected-expected.json'),MIXER_REVIEW_SOURCE=str(out/'candidate'))
        (out/'runtime').mkdir();run(['python3','-B',out/'inputs/independent-runtime.py'],env=env,timeout=60)
        shutil.copyfile(HERE/'extra-runtime.py',out/'executed-extra-runtime.py');(out/'extra-runtime').mkdir();env['MIXER_AUTHZ_OUT']=str(out/'extra-runtime')
        run(['python3','-B',out/'executed-extra-runtime.py'],env=env,timeout=60)
        # Prove every executed candidate/input byte remained frozen.
        for item in source:assert sha((out/'candidate'/item['path']).read_bytes())==item['sha256']
        for item in bindings:assert sha((out/item['copy']).read_bytes())==item['sha256'] and (out/item['copy']).read_bytes()==(ROOT/item['path']).read_bytes()
        receipt['source_and_inputs_unchanged']=True;ok=True
    except Exception as exc:receipt['error']=repr(exc);(out/'failure.log').write_text(traceback.format_exc())
    finally:
        if data and (started or (data/'postmaster.pid').exists()):run(['pg_ctl','-D',data,'-m','immediate','-w','stop'],check=False)
        if scratch and (scratch/'postgres.log').exists():shutil.copyfile(scratch/'postgres.log',out/'postgres.log')
        stopped=not data or not(data/'postmaster.pid').exists()
        if scratch and stopped:shutil.rmtree(scratch)
        receipt['cleanup']={'owned_cluster_stopped':stopped,'owned_scratch_removed':not scratch or not scratch.exists(),'tcp_listener_opened':False,'other_processes_touched':False,'native_or_phone_runs':False}
        receipt.update(success=ok,finished_utc=utc());(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
    return 0 if ok else 1
if __name__=='__main__':sys.exit(main())
