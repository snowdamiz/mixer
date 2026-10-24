#!/usr/bin/env python3
"""Execute the bounded models and one disposable socket-only PG fixture."""
import argparse,datetime,gzip,hashlib,json,os,pathlib,platform,shutil,subprocess,sys,tempfile,time,traceback
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def js(p):return json.loads(p.read_bytes())
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args();out=pathlib.Path(args.out).resolve();assert out.parent==HERE;out.mkdir(exist_ok=False)
    commands=[];receipt={'schema':1,'started_utc':utc(),'success':False,'source_digest':js(HERE/'delta-manifest.json')['candidate_source_digest'],'root_acceptance':False,'ga_acceptance':False}
    # Bound executable scripts before any execution, then verify their bytes at end.
    executed=['run.py','runtime-tests.py','model-tests.py','replay-boundaries.py','replay-extra-probes.py']
    for name in executed:shutil.copyfile(HERE/name,out/('executed-'+name))
    def run(argv,env=None,timeout=60,check=True):
        rec={'argv':list(map(str,argv)),'cwd':str(ROOT),'started_utc':utc(),'timeout_seconds':timeout};t=time.monotonic()
        if env:rec['environment_overrides']={k:v for k,v in env.items() if k.startswith('MIXER_') or k=='PYTHONDONTWRITEBYTECODE'}
        try:
            p=subprocess.run(rec['argv'],cwd=ROOT,capture_output=True,text=True,env=env,timeout=timeout);rec.update(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,stdout_sha256=sha(p.stdout.encode()),stderr_sha256=sha(p.stderr.encode()))
        except Exception as exc:rec.update(error=repr(exc),exit_code=None);raise
        finally:rec['seconds']=time.monotonic()-t;commands.append(rec);save(out/'commands.json',commands)
        if check and p.returncode:raise RuntimeError(rec)
        return p
    scratch=None;data=None;started=False;ok=False
    try:
        receipt['head']=run(['git','rev-parse','HEAD']).stdout.strip();receipt['tree']=run(['git','rev-parse','HEAD^{tree}']).stdout.strip();receipt['platform']=platform.platform()
        tools={}
        for name in ['python3','postgres','pg_ctl','initdb','psql','createdb','pg_config']:
            p=pathlib.Path(shutil.which(name)).resolve();tools[name]={'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes()),'version':run([name,'--version']).stdout.strip()}
        lib=pathlib.Path(run(['pg_config','--libdir']).stdout.strip())/'libpq.5.dylib';tools['libpq']={'path':str(lib.resolve()),'sha256':sha(lib.read_bytes())};save(out/'tool-manifest.json',tools)
        # Read-only checks of both frozen predecessors; full original runtime
        # counts remain reused evidence, never described as fresh execution.
        for folder,name,countkey,count in [('hosted-authority-catalog-shape-correction','producer','bindings',277),('hosted-authority-catalog-shape-review','review','review_bindings',115)]:
            result=run(['python3','-B',ROOT/'verification'/folder/'check.py']);observed=json.loads(result.stdout);assert observed[countkey]==count;receipt[name+'_check']=observed
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',MIXER_SHAPE_PACKET=str(HERE))
        run(['python3','-B',HERE/'replay-boundaries.py','--out',out/'models'],env=env)
        run(['python3','-B',HERE/'replay-extra-probes.py','--packet',HERE,'--out',out/'extra-models.json'],env=env)
        run(['python3','-B',HERE/'model-tests.py','--out',out/'focused-models.json'],env=env)
        scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-catalog-wildcard-',dir='/private/tmp')).resolve();data=scratch/'pg';sock=scratch/'socket';sock.mkdir(mode=0o700);receipt['scratch']=str(scratch)
        run(['initdb','-D',data,'-A','trust','--no-locale','--encoding=UTF8'])
        run(['pg_ctl','-D',data,'-l',scratch/'postgres.log','-o',f"-F -k {sock} -c listen_addresses='' -c unix_socket_permissions=0700",'-w','start']);started=True
        run(['createdb','-h',sock,'authority_contract'])
        padding='CREATE SCHEMA wildcard_padding;'+''.join(f'CREATE TABLE wildcard_padding.p{i}(a integer);' for i in range(107))
        run(['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-c',padding])
        run(['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-f',HERE/'candidate/frozen/schema.sql'])
        run(['createdb','-h',sock,'-T','authority_contract','*'])
        (out/'runtime').mkdir();env.update(MIXER_AUTHZ_SOCKET=str(sock),MIXER_AUTHZ_OUT=str(out/'runtime'),MIXER_AUTHZ_EXPECTED=str(HERE/'selected-expected.json'),MIXER_REVIEW_SOURCE=str(HERE/'candidate'),MIXER_WILDCARD_PRIOR=str(HERE/'inputs/verification/hosted-authority-catalog-review/attempt-2/independent/observations/001.json.gz'))
        run(['python3','-B',HERE/'runtime-tests.py'],env=env)
        for entry in js(HERE/'source-manifest.json'):assert sha((HERE/'candidate'/entry['path']).read_bytes())==entry['sha256']
        for entry in js(HERE/'input-manifest.json'):assert (HERE/entry['copy']).read_bytes()==(ROOT/entry['path']).read_bytes()
        for name in executed:assert (HERE/name).read_bytes()==(out/('executed-'+name)).read_bytes()
        receipt['source_inputs_and_scripts_unchanged']=True;ok=True
    except Exception as exc:receipt['error']=repr(exc);(out/'failure.log').write_text(traceback.format_exc())
    finally:
        if data and (started or (data/'postmaster.pid').exists()):run(['pg_ctl','-D',data,'-m','immediate','-w','stop'],check=False)
        if scratch and (scratch/'postgres.log').exists():shutil.copyfile(scratch/'postgres.log',out/'postgres.log')
        stopped=not data or not (data/'postmaster.pid').exists()
        if scratch and stopped:shutil.rmtree(scratch)
        receipt['cleanup']={'owned_cluster_stopped':stopped,'owned_scratch_removed':not scratch or not scratch.exists(),'tcp_listener_opened':False,'other_processes_touched':False,'native_or_phone_runs':False}
        # Preserve large complete command/SQL outputs as deterministic gzip bytes.
        compression=[]
        for p in [out/'commands.json',out/'runtime/sql-commands.json']:
            if p.exists():
                b=p.read_bytes();target=p.with_suffix(p.suffix+'.gz');target.write_bytes(gzip.compress(b,mtime=0));compression.append({'original':str(p.relative_to(out)),'compressed':str(target.relative_to(out)),'bytes':len(b),'sha256':sha(b),'compressed_sha256':sha(target.read_bytes())});p.unlink()
        save(out/'compression.json',compression);receipt.update(success=ok,finished_utc=utc());save(out/'receipt.json',receipt);print(json.dumps(receipt,indent=2))
    return 0 if ok else 1
if __name__=='__main__':sys.exit(main())
