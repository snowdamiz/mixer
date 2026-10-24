#!/usr/bin/env python3
"""Independent focused review. All PostgreSQL/process mutations are owned scratch."""
import datetime, gzip, hashlib, json, os, pathlib, platform, shutil, subprocess, sys, tarfile, tempfile, time, traceback
sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/hosted-catalog-inspector'
def sha(b): return hashlib.sha256(b).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,v): p.write_text(json.dumps(v, indent=2, sort_keys=True)+'\n')
def main():
    out = HERE / sys.argv[1]
    assert out.parent == HERE
    out.mkdir(exist_ok=False)
    shutil.copyfile(HERE/'run.py',out/'executed-run.py')
    shutil.copyfile(HERE/'review_test.exs',out/'executed-review-test.exs')
    commands=[]; scratch=None; data=None; success=False
    receipt={'schema':1,'scope':'independent frozen inspector and isolated observer-profile prerequisite review only','started_utc':now(),'success':False}
    def run(label, argv, cwd=ROOT, env=None, timeout=60, check=True):
        rec={'label':label,'argv':list(map(str,argv)),'cwd':str(cwd),'started_utc':now(),'timeout_seconds':timeout}
        if env: rec['environment_overrides']={k:v for k,v in env.items() if k.startswith('MIXER_REVIEW_') or k in ['MIX_ENV','ERL_FLAGS','ERL_CRASH_DUMP']}
        start=time.monotonic(); log=out/(label+'.log')
        try:
            p=subprocess.run(rec['argv'],cwd=cwd,env=env,capture_output=True,timeout=timeout)
            log.write_bytes(p.stdout+p.stderr)
            rec.update(exit_code=p.returncode,stdout_sha256=sha(p.stdout),stderr_sha256=sha(p.stderr),log=log.name,log_sha256=sha(log.read_bytes()))
        except Exception as exc:
            rec.update(exit_code=None,error=repr(exc)); raise
        finally:
            rec['elapsed_seconds']=time.monotonic()-start; commands.append(rec);save(out/'commands.json',commands)
        if check and p.returncode: raise RuntimeError(label+' failed: '+str(p.returncode))
        return p
    try:
        receipt['head']=run('head',['git','rev-parse','HEAD']).stdout.decode().strip()
        receipt['head_tree']=run('head-tree',['git','rev-parse','HEAD^{tree}']).stdout.decode().strip()
        run('worktree-status',['git','status','--short'])
        receipt['platform']=platform.platform()
        run('frozen-packet-check',['python3','-B',PRODUCER/'check.py'])
        pr=json.loads((PRODUCER/'receipt.json').read_bytes())
        receipt['frozen_producer']={'receipt_sha256':sha((PRODUCER/'receipt.json').read_bytes()),'source_digest':pr['source_digest'],'component_source_digest':pr['component_source_digest'],'dependency_digest':pr['dependency_digest'],'baseline_sha256':pr['baseline_sha256'],'observer_profile_sha256':pr['observer_profile_sha256'],'archive_sha256':sha((PRODUCER/'attempt-7/source-and-dependencies.tar.gz').read_bytes())}
        tools={}
        for name in ['python3','elixir','mix','erl','postgres','pg_ctl','initdb','psql','createdb']:
            p=pathlib.Path(shutil.which(name)).resolve()
            v=run('version-'+name,[p,'+V' if name=='erl' else '--version'])
            tools[name]={'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes()),'version':(v.stdout+v.stderr).decode().strip()}
        save(out/'tools.json',tools)
        scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-inspector-independent-',dir='/private/tmp')).resolve()
        receipt['scratch']=str(scratch)
        with tarfile.open(PRODUCER/'attempt-7/source-and-dependencies.tar.gz') as archive:
            archive.extractall(scratch,filter='data')
        for manifest, prefix in [('source-manifest.json',''),('dependency-manifest.json','component/deps/')]:
            entries=json.loads((PRODUCER/'attempt-7'/manifest).read_bytes())
            for item in entries:
                p=scratch/(prefix+item['path']);assert p.stat().st_size==item['bytes'] and sha(p.read_bytes())==item['sha256']
        source=scratch/'component';shutil.copyfile(HERE/'review_test.exs',source/'test/review_test.exs')
        cps=list(range(1,33))+[34,47,92,126,127,128,159,255,256,2047,2048,0x7fff,0xd7ff,0xe000,0xffff,0x10000,0x1f642,0x10ffff]
        values=[chr(c) for c in cps]+[{chr(c):[chr(c),'a',True,None,4294967295]} for c in cps]+[['\x7f','\u0080','\u00e9','\U0001f642','A','\n','\x01'],{'z':'\x7f','é':'😀','a':[False,0,-1]}]
        vectors=[{'value':v,'canonical':json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)} for v in values]
        save(out/'canonical-vectors.json',vectors)
        save(out/'review-source-manifest.json',[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in [HERE/'run.py',HERE/'review_test.exs',out/'canonical-vectors.json']])
        evidence=out/'evidence';evidence.mkdir()
        env=dict(os.environ,MIX_ENV='test',ERL_FLAGS='+S 4:4',ERL_CRASH_DUMP=str(scratch/'erl_crash.dump'),MIXER_REVIEW_OUT=str(evidence),MIXER_REVIEW_INPUTS=str(scratch/'inputs'),MIXER_REVIEW_VECTORS=str(out/'canonical-vectors.json'))
        run('deps-compile',['mix','deps.compile'],source,env,120)
        run('compile',['mix','compile','--warnings-as-errors'],source,env)
        data=scratch/'pg';sock=scratch/'socket';sock.mkdir(mode=0o700)
        run('initdb',['initdb','-D',data,'-A','trust','--no-locale','--encoding=UTF8'])
        run('pg-start',['pg_ctl','-D',data,'-l',scratch/'postgres.log','-o',f"-F -k {sock} -c listen_addresses='' -c unix_socket_permissions=0700",'-w','start'])
        run('create-db',['createdb','-h',sock,'authority_contract'])
        # Different portable transport OIDs, while the selected semantic manifest stays fixed.
        run('padding',['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-c','CREATE SCHEMA inspector_padding;'+''.join(f'CREATE TABLE inspector_padding.r{i}(v integer);' for i in range(97))])
        run('schema',['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-f',scratch/'inputs/schema.sql'])
        run('observer-bootstrap',['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-f',scratch/'inputs/observer-bootstrap.sql'])
        env['MIXER_REVIEW_SOCKET']=str(sock)
        run('independent-tests',['mix','test',*(sys.argv[2:] or ['test/review_test.exs']),'--trace','--warnings-as-errors'],source,env,90)
        if (evidence/'independent-baseline.json.gz').exists():
            sys.path.insert(0,str(scratch/'inputs/oracle'));import inspector
            raw=inspector.decode(gzip.decompress((evidence/'independent-baseline.json.gz').read_bytes()))
            profile=json.loads((source/'priv/observer-profile.json').read_bytes());baseline=json.loads((source/'priv/selected-expected.json').read_bytes())
            assert inspector.validate(raw,profile)==profile
            old_rejected=False
            try: inspector.validate(raw,baseline)
            except ValueError: old_rejected=True
            assert old_rejected
            save(out/'python-oracle.json',{'passed':True,'actual_raw_matches_selected_observer_profile':True,'original_manifest_rejects_observer_CONNECT':True,'original_raw_source':'own fresh actual PostgreSQL capture','counts':{k:len(raw['enforcement'][k]) for k in ['relations','constraints','indexes','triggers']}})
        success=True
    except Exception as exc:
        receipt['error']=repr(exc);(out/'failure.log').write_text(traceback.format_exc())
    finally:
        if data and (data/'postmaster.pid').exists():
            run('pg-stop',['pg_ctl','-D',data,'-m','immediate','-w','stop'],check=False)
        if scratch and (scratch/'postgres.log').exists():shutil.copyfile(scratch/'postgres.log',out/'postgres.log')
        if scratch and (scratch/'erl_crash.dump').exists():shutil.copyfile(scratch/'erl_crash.dump',out/'erl_crash.dump')
        stopped=not data or not (data/'postmaster.pid').exists()
        if scratch and stopped:shutil.rmtree(scratch)
        receipt.update(success=success,finished_utc=now(),cleanup={'owned_cluster_stopped':stopped,'owned_scratch_removed':not scratch or not scratch.exists(),'tcp_listener_opened':False,'other_projects_touched':False,'native_or_phone_runs':False})
        save(out/'receipt.json',receipt)
        print(json.dumps(receipt,indent=2))
    return 0 if success else 1
if __name__=='__main__':sys.exit(main())
