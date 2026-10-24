#!/usr/bin/env python3
"""One independent narrow review attempt with complete commands and cleanup."""
import argparse,datetime,gzip,hashlib,json,os,pathlib,platform,shutil,subprocess,sys,tempfile,time,traceback
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];PACKET=HERE/'frozen/verification/hosted-catalog-wildcard-correction'
def sha(b):return hashlib.sha256(b).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def js(p):return json.loads(p.read_bytes())
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();out=pathlib.Path(a.out).resolve();assert out.parent==HERE;out.mkdir(exist_ok=False)
    commands=[];r={'schema':1,'started_utc':utc(),'success':False,'candidate_source_digest':'3760cbfe5bb28407ce58d678eef22b064a960126d659df031cf11007b789d6d8','producer_receipt_sha256':'cc82538ba0709c831cf2b0579109a93cd419a972318fb84576e8ec03071d295f','root_acceptance':False,'product_startup_inspector':False,'ga_acceptance':False}
    for name in ['prepare.py','run.py','model-review.py']:shutil.copyfile(HERE/name,out/('executed-'+name))
    def run(argv,env=None,timeout=60,check=True):
        c={'argv':list(map(str,argv)),'cwd':str(ROOT),'started_utc':utc(),'timeout_seconds':timeout};t=time.monotonic()
        if env:c['environment_overrides']={k:v for k,v in env.items() if k.startswith('MIXER_') or k=='PYTHONDONTWRITEBYTECODE'}
        try:
            p=subprocess.run(c['argv'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=timeout);c.update(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,stdout_sha256=sha(p.stdout.encode()),stderr_sha256=sha(p.stderr.encode()))
        except Exception as exc:c.update(error=repr(exc),exit_code=None);raise
        finally:c['seconds']=time.monotonic()-t;commands.append(c);save(out/'commands.json',commands)
        if check and p.returncode:raise RuntimeError(c)
        return p
    scratch=None;data=None;started=False;ok=False
    try:
        r['head']=run(['git','rev-parse','HEAD']).stdout.strip();r['tree']=run(['git','rev-parse','HEAD^{tree}']).stdout.strip();r['platform']=platform.platform();r['initial_git_status']=run(['git','status','--porcelain=v1']).stdout
        tools={}
        for name in ['python3','postgres','pg_ctl','initdb','psql','createdb','pg_config']:
            path=pathlib.Path(shutil.which(name)).resolve();tools[name]={'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path.read_bytes()),'version':run([name,'--version']).stdout.strip()}
        lib=pathlib.Path(run(['pg_config','--libdir']).stdout.strip())/'libpq.5.dylib';tools['libpq']={'path':str(lib.resolve()),'sha256':sha(lib.read_bytes())};save(out/'tool-manifest.json',tools)
        run(['python3','-B',HERE/'prepare.py'])
        for folder,key,count in [('hosted-catalog-wildcard-correction','bindings',96),('hosted-authority-catalog-shape-correction','bindings',277),('hosted-authority-catalog-shape-review','review_bindings',115)]:
            observed=json.loads(run(['python3','-B',ROOT/'verification'/folder/'check.py']).stdout);assert observed[key]==count;r[folder]=observed
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');run(['python3','-B',HERE/'model-review.py','--out',out/'model-review.json'],env=env)
        scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-wildcard-independent-',dir='/private/tmp')).resolve();data=scratch/'pg';sock=scratch/'socket';sock.mkdir(mode=0o700);r['scratch']=str(scratch)
        run(['initdb','-D',data,'-A','trust','--no-locale','--encoding=UTF8'])
        run(['pg_ctl','-D',data,'-l',scratch/'postgres.log','-o',f"-F -k {sock} -c listen_addresses='' -c unix_socket_permissions=0700",'-w','start']);started=True
        run(['createdb','-h',sock,'authority_contract'])
        padding='CREATE SCHEMA independent_wildcard_padding;'+''.join(f'CREATE TABLE independent_wildcard_padding.p{i}(a integer);' for i in range(131))
        run(['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-c',padding]);r['oid_padding_tables']=131
        run(['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-f',PACKET/'candidate/frozen/schema.sql'])
        run(['createdb','-h',sock,'-T','authority_contract','*'])
        (out/'runtime').mkdir();shutil.copyfile(PACKET/'runtime-tests.py',out/'executed-runtime-tests.py')
        env.update(MIXER_AUTHZ_SOCKET=str(sock),MIXER_AUTHZ_OUT=str(out/'runtime'),MIXER_AUTHZ_EXPECTED=str(PACKET/'selected-expected.json'),MIXER_REVIEW_SOURCE=str(PACKET/'candidate'),MIXER_WILDCARD_PRIOR=str(PACKET/'inputs/verification/hosted-authority-catalog-review/attempt-2/independent/observations/001.json.gz'))
        run(['python3','-B',PACKET/'runtime-tests.py'],env=env)
        for e in js(HERE/'input-manifest.json'):assert sha((ROOT/e['path']).read_bytes())==e['sha256'] and (ROOT/e['path']).read_bytes()==(HERE/e['copy']).read_bytes()
        for name in ['prepare.py','run.py','model-review.py']:assert (HERE/name).read_bytes()==(out/('executed-'+name)).read_bytes()
        assert (out/'executed-runtime-tests.py').read_bytes()==(PACKET/'runtime-tests.py').read_bytes();r['source_and_inputs_unchanged']=True;ok=True
    except Exception as exc:r['error']=repr(exc);(out/'failure.log').write_text(traceback.format_exc())
    finally:
        if data and (started or (data/'postmaster.pid').exists()):run(['pg_ctl','-D',data,'-m','immediate','-w','stop'],check=False)
        if scratch and (scratch/'postgres.log').exists():shutil.copyfile(scratch/'postgres.log',out/'postgres.log')
        stopped=not data or not (data/'postmaster.pid').exists()
        if scratch and stopped:shutil.rmtree(scratch)
        r['cleanup']={'owned_cluster_stopped':stopped,'owned_scratch_removed':not scratch or not scratch.exists(),'tcp_listener_opened':False,'other_processes_touched':False,'native_or_phone_runs':False}
        compressed=[]
        for p in [out/'commands.json',out/'runtime/sql-commands.json']:
            if p.exists():
                b=p.read_bytes();target=p.with_suffix(p.suffix+'.gz');target.write_bytes(gzip.compress(b,mtime=0));compressed.append({'original':str(p.relative_to(out)),'compressed':str(target.relative_to(out)),'bytes':len(b),'sha256':sha(b),'compressed_sha256':sha(target.read_bytes())});p.unlink()
        save(out/'compression.json',compressed);r.update(success=ok,finished_utc=utc());save(out/'receipt.json',r);print(json.dumps(r,indent=2))
    return 0 if ok else 1
if __name__=='__main__':sys.exit(main())
