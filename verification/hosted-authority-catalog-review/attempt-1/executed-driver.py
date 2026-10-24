#!/usr/bin/env python3
"""Reproduce frozen candidate, then independent probes in unique owned PG."""
import datetime,gzip,hashlib,json,os,pathlib,platform,shutil,subprocess,sys,tempfile,time,traceback
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRODUCER=ROOT/'verification/hosted-authority-catalog-correction'
def sha(b):return hashlib.sha256(b).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
    attempt=HERE/'attempt-1';attempt.mkdir(exist_ok=False);commands=[];started=False;scratch=None;data=None;ok=False
    receipt={'schema':1,'started_utc':utc(),'scope':'independent catalog correction review only','production_mutations':False,'native_runs':False}
    def run(argv,timeout=60,check=True,env=None):
        rec={'argv':list(map(str,argv)),'cwd':str(ROOT),'started_utc':utc(),'timeout_seconds':timeout};t=time.monotonic()
        if env:rec['environment_overrides']={k:env[k] for k in ['MIXER_AUTHZ_SOCKET','MIXER_AUTHZ_OUT','MIXER_AUTHZ_EXPECTED','MIXER_REVIEW_SOURCE','PYTHONDONTWRITEBYTECODE'] if k in env}
        try:
            p=subprocess.run(rec['argv'],cwd=ROOT,capture_output=True,text=True,timeout=timeout,env=env);rec.update(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)
        except Exception as exc:rec['error']=repr(exc);raise
        finally:rec['seconds']=time.monotonic()-t;commands.append(rec);(attempt/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        if check and p.returncode:raise RuntimeError(rec)
        return p
    try:
        receipt['observed_head']=run(['git','rev-parse','HEAD']).stdout.strip();receipt['observed_tree']=run(['git','rev-parse','HEAD^{tree}']).stdout.strip()
        receipt['tools']={a[0]:run(a).stdout.strip() for a in [['python3','--version'],['postgres','--version'],['pg_ctl','--version'],['psql','--version'],['pg_config','--libdir']]};receipt['platform']=platform.platform();receipt['python_detail']=sys.version
        paths=['AGENTS.md','mixer-product-plan.md','docs/hosted-authority-schema-corrections.md','verification/hosted-authority-schema-root-review/correction-selection.json','docs/hosted-authority-catalog-correction.md']
        paths += ['verification/hosted-authority-catalog-correction/'+p for p in ['receipt.json','artifact-manifest.json','selected-expected.json','input-manifest.json','delta-manifest.json','run.py','check.py']]
        inputs=[]
        for rel in paths:
            p=ROOT/rel;b=p.read_bytes();target=attempt/'inputs'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b);inputs.append({'path':rel,'copy':str(target.relative_to(HERE)),'bytes':len(b),'sha256':sha(b)})
        (attempt/'input-manifest.json').write_text(json.dumps(inputs,indent=2)+'\n')
        source=attempt/'source';shutil.copytree(PRODUCER/'candidate',source)
        manifest=[{'path':str(p.relative_to(source)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(source.rglob('*')) if p.is_file()]
        (attempt/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');receipt['candidate_source_digest']=sha(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode())
        assert receipt['candidate_source_digest']=='8448b889f9050f9f160b8982bc929e1eacb5ca0c522cd3c7358404b331c987a0'
        shutil.copyfile(HERE/'adversarial.py',attempt/'executed-adversarial.py');shutil.copyfile(__file__,attempt/'executed-driver.py')
        receipt['producer_integrity_stdout']=run(['python3','-B',PRODUCER/'check.py']).stdout
        receipt['candidate_fresh_replay_stdout']=run(['python3','-B',PRODUCER/'run.py','--out',attempt/'fresh-replay','--oid-padding','53'],timeout=180).stdout
        scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-catalog-review-',dir='/private/tmp')).resolve();sock=scratch/'socket';sock.mkdir(mode=0o700);data=scratch/'pg';receipt['scratch']=str(scratch)
        run(['initdb','-D',data,'-A','trust','--no-locale','--encoding=UTF8'])
        run(['pg_ctl','-D',data,'-l',scratch/'postgres.log','-o',f"-F -k {sock} -c listen_addresses='' -c unix_socket_permissions=0700",'-w','start']);started=True
        run(['createdb','-h',sock,'authority_contract'])
        run(['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-c','CREATE SCHEMA review_oid_padding;'+''.join(f'CREATE TABLE review_oid_padding.padding_{i}(a integer);' for i in range(61))])
        run(['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-f',source/'frozen/schema.sql'])
        output=attempt/'independent';output.mkdir()
        env=dict(os.environ,MIXER_AUTHZ_SOCKET=str(sock),MIXER_AUTHZ_OUT=str(output),MIXER_AUTHZ_EXPECTED=str(attempt/'inputs/verification/hosted-authority-catalog-correction/selected-expected.json'),MIXER_REVIEW_SOURCE=str(source),PYTHONDONTWRITEBYTECODE='1')
        p=run(['python3','-B',attempt/'executed-adversarial.py'],timeout=120,check=False,env=env)
        receipt['independent_exit_code']=p.returncode;receipt['independent_stdout']=p.stdout
        if p.returncode:raise RuntimeError('independent adversarial probe failure; see retained output')
        ok=True
    except Exception as exc:receipt['error']=repr(exc);(attempt/'failure.log').write_text(traceback.format_exc())
    finally:
        if data and (started or (data/'postmaster.pid').exists()):run(['pg_ctl','-D',data,'-m','immediate','-w','stop'],check=False)
        if scratch and (scratch/'postgres.log').exists():shutil.copyfile(scratch/'postgres.log',attempt/'postgres.log')
        stopped=not data or not (data/'postmaster.pid').exists()
        if scratch and stopped:shutil.rmtree(scratch)
        receipt.update(success=ok,finished_utc=utc(),cleanup={'owned_cluster_stopped':stopped,'owned_scratch_removed':not scratch or not scratch.exists(),'tcp_listener_opened':False,'other_projects_touched':False,'native_or_phone_runs':False})
        (attempt/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps({k:v for k,v in receipt.items() if not k.endswith('_stdout')},indent=2))
    return 0 if ok else 1
if __name__=='__main__':sys.exit(main())
