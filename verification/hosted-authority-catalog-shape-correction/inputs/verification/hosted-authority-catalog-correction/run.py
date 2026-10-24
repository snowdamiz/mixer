#!/usr/bin/env python3
"""Fresh standalone recipe. Selection is explicit; replay never rewrites it.

  python3 -B run.py --select --out selection
  python3 -B run.py --out attempt-1
Use an absolute out directory for independent reproduction. Refuses overwrite.
"""
import argparse,datetime,gzip,hashlib,json,os,pathlib,platform,shutil,subprocess,sys,tempfile,time,traceback
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def compress_outputs(out):
    entries=[]
    for p in sorted(out.rglob('*.json')):
        if p.stat().st_size<128000:continue
        b=p.read_bytes();target=p.with_suffix(p.suffix+'.gz');target.write_bytes(gzip.compress(b,mtime=0))
        assert gzip.decompress(target.read_bytes())==b
        entries.append({'path':str(p.relative_to(out)),'compressed':str(target.relative_to(out)),'bytes':len(b),'sha256':sha(b),'compressed_sha256':sha(target.read_bytes())});p.unlink()
    (out/'compression.json').write_text(json.dumps(entries,indent=2)+'\n')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--select',action='store_true');ap.add_argument('--expected',default=str(HERE/'selected-expected.json'));ap.add_argument('--oid-padding',type=int,default=0);args=ap.parse_args()
    out=pathlib.Path(args.out);out=out if out.is_absolute() else HERE/out
    out.mkdir(parents=True,exist_ok=False);candidate=out/'source';shutil.copytree(HERE/'candidate',candidate);shutil.copyfile(__file__,out/'driver.py')
    source=[{'path':str(p.relative_to(candidate)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(candidate.rglob('*')) if p.is_file()]
    (out/'source-manifest.json').write_text(json.dumps(source,indent=2)+'\n')
    scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-authority-correction-',dir='/private/tmp')).resolve();sock=scratch/'socket';sock.mkdir(mode=0o700);data=scratch/'pg';commands=[];started=False;ok=False
    receipt={'schema':1,'started_utc':utc(),'scope':'isolated current-authority catalog correction prerequisite only','scratch':str(scratch),'selection':args.select,'oid_padding_objects':args.oid_padding,'source_digest':sha(json.dumps(source,sort_keys=True,separators=(',',':')).encode()),'driver_sha256':sha((out/'driver.py').read_bytes())}
    def run(argv,timeout=30,check=True,env=None):
        rec={'argv':list(map(str,argv)),'cwd':str(ROOT),'started_utc':utc(),'timeout_seconds':timeout};t=time.monotonic()
        if env:rec['environment_overrides']={k:env[k] for k in ['MIXER_AUTHZ_SOCKET','MIXER_AUTHZ_OUT','MIXER_AUTHZ_EXPECTED','PYTHONDONTWRITEBYTECODE'] if k in env}
        try:
            p=subprocess.run(rec['argv'],cwd=ROOT,capture_output=True,text=True,timeout=timeout,env=env);rec.update(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)
        except Exception as exc:rec['error']=repr(exc);raise
        finally:
            rec['seconds']=time.monotonic()-t;commands.append(rec);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        if check and p.returncode:raise RuntimeError(rec)
        return p
    try:
        receipt['observed_head']=run(['git','rev-parse','HEAD']).stdout.strip();receipt['observed_tree']=run(['git','rev-parse','HEAD^{tree}']).stdout.strip()
        receipt['tools']={a[0]:run(a).stdout.strip() for a in [['python3','--version'],['postgres','--version'],['pg_ctl','--version'],['psql','--version'],['pg_config','--libdir']]}
        receipt['tools']['platform']=platform.platform();receipt['tools']['python_detail']=sys.version
        lib=pathlib.Path(receipt['tools']['pg_config'])/'libpq.5.dylib';receipt['tools']['libpq']={'path':str(lib.resolve()),'sha256':sha(lib.read_bytes())}
        receipt['producer_integrity']=run(['python3','-B',ROOT/'verification/hosted-authority-schema-contract/check.py']).stdout
        receipt['review_integrity']=run(['python3','-B',ROOT/'verification/hosted-authority-schema-review/check.py']).stdout
        run(['initdb','-D',data,'-A','trust','--no-locale','--encoding=UTF8'])
        run(['pg_ctl','-D',data,'-l',scratch/'postgres.log','-o',f"-F -k {sock} -c listen_addresses='' -c unix_socket_permissions=0700",'-w','start']);started=True
        run(['createdb','-h',sock,'authority_contract'])
        if args.oid_padding:
            assert 0<args.oid_padding<=100
            run(['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-c','CREATE SCHEMA correction_oid_padding;'+''.join(f'CREATE TABLE correction_oid_padding.padding_{i}(a integer);' for i in range(args.oid_padding))])
        run(['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-f',candidate/'frozen/schema.sql'])
        env=dict(os.environ,MIXER_AUTHZ_SOCKET=str(sock),PYTHONDONTWRITEBYTECODE='1',MIXER_AUTHZ_OUT=str(out),MIXER_AUTHZ_EXPECTED=str(pathlib.Path(args.expected).resolve()))
        # A copied harness prelude gives actual libpq connections without running
        # tests during selection; its bytes remain bound to the frozen producer.
        harness="import json,pathlib,sys\nsys.path.insert(0,"+repr(str(candidate))+ ")\nsource=pathlib.Path("+repr(str(candidate/'frozen/tests.py'))+").read_text()\nexec(compile(source[:source.index('def success(')],'frozen-fixture','exec'),globals())\nfrom inspector import inspect,safe_selection,validate\nwith DB('mixer_hosted_runtime') as runtime:raw=inspect(ADMIN,runtime)\nnormalized=safe_selection(raw)\npathlib.Path("+repr(str(out/'raw-baseline.json'))+").write_text(json.dumps(raw,sort_keys=True,indent=2)+'\\n')\npathlib.Path("+repr(str(out/'normalized-baseline.json'))+").write_text(json.dumps(normalized,sort_keys=True,indent=2)+'\\n')\nADMIN.close()\n"
        run(['python3','-B','-c',harness],env=env)
        normalized=(out/'normalized-baseline.json').read_bytes();receipt['normalized_baseline_sha256']=sha(normalized)
        expected=pathlib.Path(args.expected).resolve()
        if args.select:
            if expected.exists():raise RuntimeError('selection refuses to overwrite frozen expected manifest')
            expected.write_bytes(normalized);receipt['expected_manifest_path']=str(expected)
        else:
            assert normalized==expected.read_bytes(),'fresh baseline differs from separately frozen selected manifest'
            receipt['expected_manifest_sha256']=sha(expected.read_bytes())
            replay=out/'replay';replay.mkdir();env['MIXER_AUTHZ_OUT']=str(replay)
            run(['python3','-B',candidate/'frozen/tests.py'],timeout=100,env=env)
            # Preserve reviewer bytes and original path expectations, including
            # the five documented gap observations (they are not security passes).
            review=out/'review';(review/'replay').mkdir(parents=True);shutil.copytree(candidate/'frozen',review/'replay/source');shutil.copyfile(candidate/'frozen/reviewer.py',review/'adversarial.py');(review/'adversarial').mkdir()
            env['MIXER_AUTHZ_OUT']=str(review/'adversarial');run(['python3','-B',review/'adversarial.py'],timeout=100,env=env)
            corrected=out/'corrected';corrected.mkdir();env['MIXER_AUTHZ_OUT']=str(corrected)
            run(['python3','-B',candidate/'tests.py'],timeout=100,env=env)
        ok=True
    except Exception as exc:
        receipt['error']=repr(exc);(out/'failure.log').write_text(traceback.format_exc())
    finally:
        if started or (data/'postmaster.pid').exists():run(['pg_ctl','-D',data,'-m','immediate','-w','stop'],check=False)
        if (scratch/'postgres.log').exists():shutil.copyfile(scratch/'postgres.log',out/'postgres.log')
        stopped=not(data/'postmaster.pid').exists()
        if stopped:shutil.rmtree(scratch)
        else:ok=False;receipt['cleanup_error']='owned postmaster still present; scratch retained for recovery'
        receipt.update(success=ok,finished_utc=utc(),cleanup={'owned_cluster_stopped':stopped,'owned_scratch_removed':not scratch.exists(),'tcp_listener_opened':False,'other_processes_touched':False,'native_or_phone_runs':False})
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');compress_outputs(out);print(json.dumps({k:v for k,v in receipt.items() if k not in ['producer_integrity','review_integrity','error']},indent=2))
    return 0 if ok else 1
if __name__=='__main__':sys.exit(main())
