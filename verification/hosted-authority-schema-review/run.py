#!/usr/bin/env python3
"""Independent replay of frozen run-9 plus reviewer-owned adversarial probes."""
import datetime, hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile, time, traceback
sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
def sha(b): return hashlib.sha256(b).hexdigest()
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
    scratch = pathlib.Path(tempfile.mkdtemp(prefix='mixer-authz-schema-review-', dir='/private/tmp')).resolve()
    sock = scratch/'socket'; sock.mkdir(mode=0o700)
    data = scratch/'pg'; commands=[]; started=False; ok=False
    receipt={'schema':1,'started_utc':utc(),'scope':'Independent local PostgreSQL current-authority prerequisite review only; no product implementation or GA acceptance','scratch':str(scratch)}
    def run(args, timeout=30, check=True, env=None):
        rec={'argv':list(map(str,args)),'cwd':str(ROOT),'started_utc':utc(),'timeout_seconds':timeout}; t=time.monotonic()
        if env: rec['environment_overrides']={k:env[k] for k in ['MIXER_AUTHZ_SOCKET','MIXER_AUTHZ_OUT','PYTHONDONTWRITEBYTECODE']}
        try:
            p=subprocess.run(rec['argv'],cwd=ROOT,capture_output=True,text=True,timeout=timeout,env=env)
            rec.update(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)
        except Exception as exc: rec['error']=repr(exc);raise
        finally:
            rec['seconds']=time.monotonic()-t; commands.append(rec); (HERE/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        if check and p.returncode: raise RuntimeError(rec)
        return p
    try:
        receipt['observed_head']=run(['git','rev-parse','HEAD']).stdout.strip()
        receipt['observed_tree']=run(['git','rev-parse','HEAD^{tree}']).stdout.strip()
        receipt['tools']={a[0]:run(a).stdout.strip() for a in [['python3','--version'],['postgres','--version'],['pg_ctl','--version'],['psql','--version'],['pg_config','--libdir']]}
        receipt['producer_integrity']=run(['python3','-B',ROOT/'verification/hosted-authority-schema-contract/check.py']).stdout
        receipt['producer_contract_sha256']=sha((ROOT/'docs/hosted-authority-schema-contract.md').read_bytes())
        receipt['producer_receipt_sha256']=sha((ROOT/'verification/hosted-authority-schema-contract/receipt.json').read_bytes())
        assert receipt['producer_contract_sha256']=='d12d3b3a0484289f9990990f104bd3aaaff19eb4488caa6eca730ecdc938fbbd'
        assert receipt['producer_receipt_sha256']=='ab20a2694c537ee04f2a07c0e1208ff44a24f7e7c78d930fab9591803b28e9cb'
        source=json.loads((ROOT/'verification/hosted-authority-schema-contract/run-9/source-manifest.json').read_text())
        for ent in source:
            p=HERE/'replay/source'/pathlib.Path(ent['path']).name
            assert len(p.read_bytes())==ent['bytes'] and sha(p.read_bytes())==ent['sha256']
        receipt['frozen_source_digest']=sha(json.dumps(source,sort_keys=True,separators=(',',':')).encode())
        assert receipt['frozen_source_digest']=='ebaae05f782695d3cd9d1fcedc535f0b47cdb736167384b7dc6d8a09fa16b0de'
        (HERE/'source-manifest.json').write_text(json.dumps(source,indent=2)+'\n')
        run(['initdb','-D',data,'-A','trust','--no-locale','--encoding=UTF8'])
        run(['pg_ctl','-D',data,'-l',scratch/'postgres.log','-o',f"-F -k {sock} -c listen_addresses='' -c unix_socket_permissions=0700",'-w','start']); started=True
        run(['createdb','-h',sock,'authority_contract'])
        run(['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-f',HERE/'replay/source/schema.sql'])
        env=dict(os.environ,MIXER_AUTHZ_SOCKET=str(sock),MIXER_AUTHZ_OUT=str(HERE/'replay'),PYTHONDONTWRITEBYTECODE='1')
        run(['python3','-B',HERE/'replay/source/tests.py'],timeout=90,env=env)
        env['MIXER_AUTHZ_OUT']=str(HERE/'adversarial'); (HERE/'adversarial').mkdir(exist_ok=True)
        run(['python3','-B',HERE/'adversarial.py'],timeout=90,env=env)
        ok=True
    except Exception as exc:
        receipt['error']=repr(exc);(HERE/'failure.log').write_text(traceback.format_exc())
    finally:
        if started: run(['pg_ctl','-D',data,'-m','immediate','-w','stop'],check=False)
        if (scratch/'postgres.log').exists(): shutil.copyfile(scratch/'postgres.log',HERE/'postgres.log')
        stopped=not (data/'postmaster.pid').exists();shutil.rmtree(scratch)
        receipt.update(success=ok,finished_utc=utc(),cleanup={'owned_cluster_stopped':stopped,'owned_scratch_removed':not scratch.exists(),'tcp_listener_opened':False,'other_processes_touched':False,'native_or_phone_runs':False})
        (HERE/'execution-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
    return 0 if ok else 1
if __name__=='__main__':sys.exit(main())
