#!/usr/bin/env python3
"""Bounded fixture representation qualification; never production admission."""
import argparse
import collections
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
PG = Path('/opt/homebrew/Cellar/postgresql@17/17.11/bin')
IMAGE = 'postgres@sha256:9e2cf6287f25c3151f4c9421ccce2b17f3e60061c111a29165e0d2cdd9ff0a97'
DEPS = ['telemetry', 'decimal', 'db_connection', 'ecto', 'ecto_sql', 'postgrex', 'jason', 'oban']
MIGRATIONS = ['20261024000000_add_oban.exs','20261025000000_add_build_journals.exs','20261025000001_add_build_admission.exs','20261025000002_add_build_aggregate_limits.exs','20261025000003_add_customer_authorization.exs','20261025000004_add_authorization_state_revisions.exs','20261025000005_add_customer_artifact_storage.exs','20261025000006_add_customer_workspace_discovery.exs','20261025000007_add_browser_sessions.exs']
SOURCES = ['AGENTS.md','PLAN.md','hosted/mix.lock','hosted/lib/mixer_hosted/browser_auth/storage_schema.ex','hosted/lib/mixer_hosted/customer_artifacts/schema.ex','hosted/lib/mixer_hosted/authorization/postgres/session.ex','hosted/test/mixer_hosted/browser_auth/storage_fixture.exs','docs/hosted-browser-relation-admission-contract.md','docs/hosted-browser-relation-admission-contract-review.md','verification/hosted-browser-relation-admission-contract/relation-matrix.json','verification/hosted-browser-relation-admission-contract/receipt.json','verification/hosted-browser-relation-admission-contract-review/receipt.json'] + ['hosted/priv/repo/migrations/'+n for n in MIGRATIONS]
SOURCES += ['hosted/deps/oban/lib/oban/migration.ex','hosted/deps/oban/lib/oban/migrations/postgres.ex']+['hosted/deps/oban/lib/oban/migrations/postgres/v%02d.ex'%n for n in range(1,15)]
SOURCES += ['verification/hosted-browser-relation-representation/'+n for n in ['qualify.py','install.exs','snapshot.sql']]
CAPS = dict(relations=9, columns=124, constraints=109, indexes=14, triggers=53, policies=32, acl=512, table_effective=27, column_effective=372)

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value): Path(path).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def tree(manifest): return hashlib.sha256(''.join(p+'\t'+h+'\n' for p,h in sorted(manifest.items())).encode()).hexdigest()
def lit(value): return "'"+value.replace("'","''")+"'"
def qname(value): return '"'+value.replace('"','""')+'"'
def normrel(value): return value if value is None or value.startswith('public.') else 'public.'+value

def canonical(snapshot):
    s=copy.deepcopy(snapshot)
    s.pop('environment',None)
    mapping={r['name']: r['relation']+':'+','.join(r['columns'])+':'+str(r['predicate']) for r in s['indexes']}
    for family, rows in s.items():
        for row in rows:
            if 'relation' in row: row['relation']=normrel(row['relation'])
            for field in ['target','opposite','constraint_relation']:
                if field in row and row[field] is not None: row[field]=normrel(row[field])
            if row.get('index') is not None:
                row['index']=mapping.get(row['index'],row['index'])
            if family=='constraints': row.pop('conname'); row.pop('definition')
            if family=='indexes':
                if row['name']!='mixer_browser_one_attempt': row.pop('name')
            if family=='triggers':
                row.pop('constraint_name'); row.pop('definition')
                if row['tgisinternal']: row.pop('tgname')
        rows.sort(key=lambda r:json.dumps(r,sort_keys=True))
    return s


def source_oracle_sql(matrix):
    # Compile literal reviewed source expressions on independently constructed
    # temporary columns, never copy constraints/defaults from the observed catalog.
    stmts=['SET search_path=pg_catalog; BEGIN;']
    for rel,t in matrix['relations'].items():
        name=rel.split('.')[1]
        specs=[]
        for c in t['columns']:
            specs.append(qname(c['name'])+' '+c['type']+(' DEFAULT '+c['default'] if c['default'] else ''))
        stmts.append('CREATE TEMP TABLE '+qname(name)+' ('+','.join(specs)+');')
        for i,expr in enumerate(t['checks']):
            stmts.append('ALTER TABLE pg_temp.'+qname(name)+' ADD CONSTRAINT source_'+str(i)+' CHECK ('+expr+');')
        for p in matrix['policies'][rel]:
            cmd='CREATE POLICY '+qname(p['name'])+' ON pg_temp.'+qname(name)+' FOR '+p['command']+' TO '+('PUBLIC' if p['roles']==['PUBLIC'] else 'browser_writer')
            if p['using'] is not None: cmd+=' USING ('+p['using']+')'
            if p['check'] is not None: cmd+=' WITH CHECK ('+p['check']+')'
            stmts.append(cmd+';')
        for i,ind in enumerate(t['extra_indexes']):
            stmts.append('CREATE UNIQUE INDEX source_index_'+str(i)+' ON pg_temp.'+qname(name)+' ('+','.join(qname(x) for x in ind['columns'])+') WHERE '+ind['predicate']+';')
    stmts.append("SELECT json_build_object('checks',(SELECT json_agg(x) FROM (SELECT 'public.'||c.relname AS relation,k.conname,pg_get_expr(k.conbin,k.conrelid,false) AS expression FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid WHERE c.relnamespace=pg_my_temp_schema() AND k.contype='c' ORDER BY c.relname,k.conname LIMIT 81) x),'defaults',(SELECT json_agg(x) FROM (SELECT 'public.'||c.relname AS relation,a.attname,pg_get_expr(d.adbin,d.adrelid,false) AS expression FROM pg_attrdef d JOIN pg_attribute a ON a.attrelid=d.adrelid AND a.attnum=d.adnum JOIN pg_class c ON c.oid=d.adrelid WHERE c.relnamespace=pg_my_temp_schema() ORDER BY c.relname,a.attname LIMIT 4) x),'policies',(SELECT json_agg(x) FROM (SELECT 'public.'||c.relname AS relation,p.polname,pg_get_expr(p.polqual,p.polrelid,false) AS using_expr,pg_get_expr(p.polwithcheck,p.polrelid,false) AS check_expr FROM pg_policy p JOIN pg_class c ON c.oid=p.polrelid WHERE c.relnamespace=pg_my_temp_schema() ORDER BY c.relname,p.polname LIMIT 33) x),'predicates',(SELECT json_agg(x) FROM (SELECT 'public.'||c.relname AS relation,pg_get_expr(i.indpred,i.indrelid,false) AS expression FROM pg_index i JOIN pg_class c ON c.oid=i.indrelid WHERE c.relnamespace=pg_my_temp_schema() AND i.indpred IS NOT NULL LIMIT 2) x)); ROLLBACK;")
    return '\n'.join(stmts)


def validate(s,m,o,major):
    checks=[]
    def verify(name,value):
        checks.append({'name':name,'passed':bool(value)})
        if not value: raise AssertionError(name)
    def relrows(f,rel): return [r for r in s[f] if normrel(r['relation'])==rel]
    verify('all family caps and exact fixed counts',all(len(s[f])==n if f!='acl' else len(s[f])<=n for f,n in CAPS.items()))
    verify('complete relation identities',set(normrel(r['relation']) for r in s['relations'])==set(m['relations']))
    verify('relation flags owner and escape metadata',all(r['relkind']=='r' and r['relpersistence']=='p' and r['relrowsecurity'] and r['relforcerowsecurity'] and r['owner']=='browser_schema_owner' and not any(r[x] for x in ['relispartition','inheritance','rules','foreign_table']) and r['reloftype']=='0' and r['relreplident']=='d' and r['partition_bound'] is None for r in s['relations']))
    types=dict(bytea='bytea',text='text',integer='int4',bigint='int8',boolean='bool')
    for rel,t in m['relations'].items():
        rows=relrows('columns',rel)
        verify(rel+' ordered columns/type/default/nullability',len(rows)==len(t['columns']) and all(r['attname']==c['name'] and r['attnum']==i+1 and r['type']=='pg_catalog.'+types[c['type']] and r['attnotnull']==(not c['nullable']) and r['default_expr']==c['default'] for i,(r,c) in enumerate(zip(rows,t['columns']))))
        verify(rel+' column structural flags and collation identity',all(not r['attisdropped'] and r['atttypmod']==-1 and r['attndims']==0 and r['attidentity']=='' and r['attgenerated']=='' and r['attislocal'] and r['attinhcount']==0 and r['collation']==('pg_catalog.default' if r['type']=='pg_catalog.text' else None) for r in rows))
        actual=[r['expression'] for r in relrows('constraints',rel) if r['contype']=='c']
        expected=[r['expression'] for r in o['checks'] if r['relation']==rel]
        verify(rel+' source-compiled CHECK multiset',collections.Counter(actual)==collections.Counter(expected))
        keyrows=relrows('constraints',rel)
        verify(rel+' PK/UNIQUE source keys',collections.Counter((r['contype'],tuple(r['columns'])) for r in keyrows if r['contype'] in ['p','u'])==collections.Counter([('p',tuple(t['primary_key']))]+[('u',tuple(u)) for u in t['unique']]))
    verify('all eighty CHECKs independently compiled',len(o['checks'])==80)
    verify('all policies source compiled',len(o['policies'])==32 and all(any(normrel(r['relation'])==p['relation'] and r['polname']==p['polname'] and r['using_expr']==p['using_expr'] and r['check_expr']==p['check_expr'] for r in s['policies']) for p in o['policies']))
    commands=dict(SELECT='r',INSERT='a',UPDATE='w',DELETE='d',ALL='*')
    verify('all policy names commands roles permissiveness',all(collections.Counter((p['polname'],p['polcmd'],tuple(p['roles']),p['polpermissive']) for p in relrows('policies',rel))==collections.Counter((p['name'],commands[p['command']],tuple('browser_writer' if x=='$writer' else x for x in p['roles']),p['permissive']) for p in ps) for rel,ps in m['policies'].items()))
    defaults=[r for r in s['columns'] if r['default_expr'] is not None]
    verify('exact three source compiled defaults',len(defaults)==3 and all(any(normrel(r['relation'])==v['relation'] and r['attname']==v['attname'] and r['default_expr']==v['expression'] for r in defaults) for v in o['defaults']))
    fast={('public.mixer_authz_profiles','state_revision'),('public.mixer_authz_bindings','revision')}
    verify('fast defaults only two bigint ALTER columns',all((r['atthasmissing'] and r['attmissingval']=='{1}') if (normrel(r['relation']),r['attname']) in fast else (not r['atthasmissing'] and r['attmissingval'] is None) for r in s['columns']))
    verify('ordinary constraint enforcement flags and kind specific noinherit',all(r['convalidated'] and r['conislocal'] and r['coninhcount']==0 and r['conparentid']=='0' and r['contypid']=='0' and r['connoinherit']==(r['contype']!='c') and r['condeferrable']==(r['contype']=='t') and r['condeferred']==(r['contype']=='t') for r in s['constraints']))
    actual=collections.Counter((normrel(r['relation']),tuple(r['columns']),normrel(r['target']),tuple(r['target_columns']),r['confmatchtype'],r['confupdtype'],r['confdeltype']) for r in s['constraints'] if r['contype']=='f')
    expected=[]
    for rel,t in m['relations'].items():
        expected += [(rel,tuple(f['columns']),f['relation'],tuple(f['referenced_columns']),f['match'],f['on_update'],f['on_delete']) for f in t['foreign_keys']]
    expected += [(f['source_relation'],tuple(f['columns']),f['relation'],tuple(f['referenced_columns']),f['match'],f['on_update'],f['on_delete']) for f in m['incoming_foreign_keys']]
    verify('exact twelve source FK groups including both incoming',actual==collections.Counter(expected))
    verify('four constraint trigger rows and constraints count',collections.Counter(r['contype'] for r in s['constraints'])==dict(c=80,p=9,u=4,f=12,t=4))
    inds={r['name']:r for r in s['indexes']}
    verify('index enforcement health flags and source key identity',all(r['namespace']=='public' and r['owner']=='browser_schema_owner' and r['amname']=='btree' and r['indnatts']==len(r['columns'])==r['indnkeyatts'] and r['indisunique'] and not any(r[x] for x in ['indnullsnotdistinct','indisexclusion','indisclustered','indcheckxmin','indisreplident','relispartition','inheritance']) and all(r[x] for x in ['indimmediate','indisvalid','indisready','indislive']) and r['expression'] is None and set(r['indoption'].split())=={'0'} for r in s['indexes']))
    verify('exact partial source predicate',sum(r['predicate'] is not None for r in s['indexes'])==1 and inds['mixer_browser_one_attempt']['predicate']==o['predicates'][0]['expression'])
    verify('constraint indexes and FK referenced index backlinks',all(r['index'] in inds and normrel(inds[r['index']]['relation'])==normrel(r['target'] if r['contype']=='f' else r['relation']) and inds[r['index']]['columns']==(r['target_columns'] if r['contype']=='f' else r['columns']) and inds[r['index']]['backing'] in [['p'],['u']] for r in s['constraints'] if r['contype'] in ['p','u','f']))
    for ind in s['indexes']:
        cs={r['attname']:r for r in relrows('columns',normrel(ind['relation']))}
        expectops=[]
        expectcoll=[]
        for name in ind['columns']:
            typ=cs[name]['type'].split('.')[1]
            sqltyp={'int4':'integer','int8':'bigint','bool':'boolean'}.get(typ,typ)
            expectops.append('pg_catalog.'+typ+'_ops:'+sqltyp+':pg_catalog.'+typ+'_ops')
            expectcoll.append('pg_catalog.default' if typ=='text' else None)
        verify('index '+ind['name']+' builtin opclass/opfamily/input/collation',ind['opclasses']==expectops and ind['collations']==expectcoll)
    builtin={'RI_FKey_check_ins()':(5,'child'),'RI_FKey_check_upd()':(17,'child'),'RI_FKey_noaction_del()':(9,'parent'),'RI_FKey_noaction_upd()':(17,'parent')}
    fks={r['conname']:r for r in s['constraints'] if r['contype']=='f'}
    ri=[t for t in s['triggers'] if t['tgisinternal']]
    verify('exact RI group and endpoint event index mapping',len(ri)==48 and all(collections.Counter(t['function'] for t in ri if t['constraint_name']==name)==collections.Counter(builtin) for name in fks) and all(t['function_namespace']=='pg_catalog' and t['function'] in builtin and t['tgtype']==builtin[t['function']][0] and normrel(t['relation'])==normrel(fks[t['constraint_name']]['relation'] if builtin[t['function']][1]=='child' else fks[t['constraint_name']]['target']) and normrel(t['opposite'])==normrel(fks[t['constraint_name']]['target'] if builtin[t['function']][1]=='child' else fks[t['constraint_name']]['relation']) and t['index']==fks[t['constraint_name']]['index'] for t in ri))
    verify('all trigger enforcement empty metadata',all(t['tgenabled']=='O' and t['tgnargs']==0 and t['args']=='' and t['tgattr']=='' and t['qual'] is None and t['tgoldtable'] is None and t['tgnewtable'] is None and t['tgparentid']=='0' and t['tgdeferrable']==(not t['tgisinternal'] and t['constraint_type']=='t') and t['tginitdeferred']==t['tgdeferrable'] for t in s['triggers']))
    users=[t for t in s['triggers'] if not t['tgisinternal']]
    def eventbits(t): return 1+(2 if t['timing']=='BEFORE' else 0)+sum({'INSERT':4,'UPDATE':16,'DELETE':8}[x] for x in t['events'])
    verify('exact five source user triggers',collections.Counter((normrel(t['relation']),t['tgname'],'public.'+t['function'],t['tgtype'],bool(t['constraint_type']=='t'),t['tgdeferrable']) for t in users)==collections.Counter((t['relation'],t['name'],t['function'],eventbits(t),t['constraint'],t['deferrable']) for t in m['user_triggers']))
    app={}
    for rel in m['relations']:
        for role in ['browser_lifecycle','browser_writer','browser_ordinary']:
            table=m['writer_grants'][rel]['table'] if role=='browser_writer' else ['SELECT'] if role=='browser_ordinary' and '.mixer_authz_' in rel else []
            app[(rel,role)]=table
    privmap={'sel':'SELECT','ins':'INSERT','upd':'UPDATE','del':'DELETE','trunc':'TRUNCATE','refs':'REFERENCES','trig':'TRIGGER','maintain':'MAINTAIN'}
    verify('all effective application table privileges',all(all(r[k]==(p in app[(normrel(r['relation']),r['role'])]) for k,p in privmap.items() if k in r) for r in s['table_effective']))
    verify('all effective application column privileges',all(all(r[k]==(p in app[(normrel(r['relation']),r['role'])] or (p=='UPDATE' and r['role']=='browser_writer' and r['attname'] in m['writer_grants'][normrel(r['relation'])]['update_columns'])) for k,p in {k:v for k,v in privmap.items() if k in ['sel','ins','upd','refs']}.items()) for r in s['column_effective']))
    raw=[]
    owner=['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER']+(['MAINTAIN'] if major==17 else [])
    for rel in m['relations']:
        raw += [(rel,None,'browser_schema_owner','browser_schema_owner',p,False) for p in owner]
        for role in ['browser_lifecycle','browser_writer','browser_ordinary']:
            raw += [(rel,None,role,'browser_schema_owner',p,False) for p in app[(rel,role)]]
        raw += [(rel,c,'browser_writer','browser_schema_owner','UPDATE',False) for c in m['writer_grants'][rel]['update_columns']]
    verify('all raw ACL owner/app/grantor/grant-option rows',collections.Counter((normrel(r['relation']),r['column_name'],r['grantee'],r['grantor'],r['privilege_type'],r['is_grantable']) for r in s['acl'])==collections.Counter(raw))
    return checks


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--major',type=int,choices=[16,17],required=True);args=parser.parse_args();major=args.major
    out=BASE/'attempts'/(dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-pg'+str(major)+'-'+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
    inputs=out/'inputs';inputs.mkdir()
    receipt={'schema':1,'major':major,'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'commands':[],'cleanup':{},'scope':'Source-pinned all-nine ordinary migrations, operator topology, clean representation qualification and fixture-only comparator mutations. No product RelationCatalog/readiness/Store/provider/native/UI/capture/phone or broad app harness.'}
    environment=dict(os.environ,ERL_FLAGS='+S 2:2',MIX_ENV='test')
    scratch=None;container=None;started=False
    def run(label,argv,check=True,data=None,timeout=30,cwd=inputs):
        argv=list(map(str,argv));entry={'label':label,'argv':argv,'cwd':str(cwd),'timeout_seconds':timeout};receipt['commands'].append(entry)
        p=subprocess.Popen(argv,cwd=cwd,env=environment,stdin=subprocess.PIPE if data is not None else None,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        try: stdout,stderr=p.communicate(data.encode() if isinstance(data,str) else data,timeout=timeout);entry['timed_out']=False
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);stdout,stderr=p.communicate(timeout=5);entry['timed_out']=True
        entry['exit_code']=p.returncode
        for suffix,content in [('stdout',stdout),('stderr',stderr)]: (out/(label+'.'+suffix)).write_bytes(content)
        if data is not None: (out/(label+'.stdin.sql')).write_bytes(data.encode() if isinstance(data,str) else data)
        if check and (p.returncode or entry['timed_out']): raise RuntimeError(label+' failed')
        return p.returncode,stdout.decode()
    try:
        manifest={}
        for rel in SOURCES:
            target=inputs/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,target);manifest[rel]=sha(target)
        write(out/'source-bindings.json',manifest);receipt['source_tree_sha256']=tree(manifest)
        _,head=run('revision',['git','-C',ROOT,'rev-parse','HEAD']);receipt['head']=head.strip()
        depdirs=[ROOT/'hosted/_build/test/lib'/dep/'ebin' for dep in DEPS]
        beams={str(p.relative_to(ROOT)):sha(p) for d in depdirs for p in sorted(d.iterdir()) if p.is_file()}
        write(out/'dependency-beams.json',beams);receipt['dependency_tree_sha256']=tree(beams)
        run('python-version',['python3','--version']);run('elixir-version',['elixir','--version']);run('psql-version',[PG/'psql','--version'])
        with socket.socket() as sock: sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        if major==17:
            scratch=Path(tempfile.mkdtemp(prefix='mixer-relation-representation-pg17-'));receipt['owned_scratch']=str(scratch)
            run('initdb',[PG/'initdb','-D',scratch/'data','-U','browser_admin','-A','trust','--no-locale','-E','UTF8'])
            started=True;run('start',[PG/'pg_ctl','-D',scratch/'data','-l',out/'server.log','-o',f"-h 127.0.0.1 -p {port} -k '' -c timezone=UTC",'-w','start'])
            admin=[PG/'psql','-X','-q','-A','-t','-h','127.0.0.1','-p',port,'-U','browser_admin','-d','postgres','-v','ON_ERROR_STOP=1']
        else:
            container='mixer-relation-representation-pg16-'+uuid.uuid4().hex[:12];receipt['owned_container']=container
            run('docker-version',['docker','version','--format','{{json .Server}}']);run('docker-image',['docker','image','inspect',IMAGE]);receipt['image']=IMAGE
            started=True;run('start',['docker','run','--detach','--rm','--name',container,'--label','mixer.fixture=relation-representation','--publish',f'127.0.0.1:{port}:5432','--env','POSTGRES_USER=browser_admin','--env','POSTGRES_HOST_AUTH_METHOD=trust','--env','POSTGRES_INITDB_ARGS=--no-locale -E UTF8',IMAGE,'-c','timezone=UTC'])
            for i in range(80):
                code,_=run('ready-'+str(i),['docker','exec',container,'pg_isready','-h','127.0.0.1','-U','browser_admin'],check=False)
                if code==0:
                    try:
                        with socket.create_connection(('127.0.0.1',port),timeout=.2): break
                    except OSError: pass
                time.sleep(.1)
            else: raise RuntimeError('owned PG16 readiness failed')
            admin=[PG/'psql','-X','-q','-A','-t','-h','127.0.0.1','-p',port,'-U','browser_admin','-d','postgres','-v','ON_ERROR_STOP=1']
        receipt['port']=port
        run('roles',admin,data=';'.join('CREATE ROLE '+role+' '+login+' NOSUPERUSER NOBYPASSRLS NOINHERIT' for role,login in [('browser_schema_owner','NOLOGIN'),('browser_writer','NOLOGIN'),('browser_lifecycle','LOGIN'),('browser_ordinary','LOGIN'),('representation_extra','NOLOGIN')])+';')
        run('database',admin,data='CREATE DATABASE browser_storage OWNER browser_schema_owner;')
        db=admin.copy();db[db.index('postgres')]='browser_storage'
        environment['REPRESENTATION_PORT']=str(port)
        run('install',['elixir']+[arg for d in depdirs for arg in ['-pa',d]]+[inputs/'verification/hosted-browser-relation-representation/install.exs'],timeout=60)
        matrix=json.loads((inputs/'verification/hosted-browser-relation-admission-contract/relation-matrix.json').read_text())
        _,oracle_output=run('source-oracle',db,data=source_oracle_sql(matrix));oracle=json.loads(oracle_output);write(out/'source-compiled-oracle.json',oracle)
        sql=(inputs/'verification/hosted-browser-relation-representation/snapshot.sql').read_text().replace('__MAINTAIN__',",has_table_privilege(role,c.oid,'MAINTAIN') AS maintain" if major==17 else '')
        _,baseline_output=run('clean-baseline',db,data=sql);snapshot=json.loads(baseline_output)
        if len(baseline_output.encode())>2*1024*1024: raise AssertionError('2MiB fixture wire cap')
        write(out/'clean-baseline.json',snapshot)
        checks=validate(snapshot,matrix,oracle,major);write(out/'semantic-checks.json',checks)
        frozen=canonical(snapshot);write(out/'frozen-expectation.json',frozen);receipt['frozen_expectation_sha256']=sha(out/'frozen-expectation.json')
        receipt['environment']=snapshot['environment'];receipt['counts']={f:len(snapshot[f]) for f in CAPS};receipt['semantic_methods_passed']=len(checks)
        # Freeze happens once above, before any attacks. Each attack rolls back.
        mutations=[
          ('extra-check','ALTER TABLE public.mixer_browser_sessions ADD CHECK (true)'),
          ('extra-column','ALTER TABLE public.mixer_browser_sessions ADD COLUMN surprise text'),
          ('disable-user-trigger','ALTER TABLE public.mixer_browser_sessions DISABLE TRIGGER mixer_browser_integrity'),
          ('disable-child-ri',"DO $x$ DECLARE n name; BEGIN SELECT tgname INTO n FROM pg_trigger WHERE tgrelid='public.mixer_browser_sessions'::regclass AND tgisinternal AND tgtype=5 LIMIT 1; EXECUTE format('ALTER TABLE public.mixer_browser_sessions DISABLE TRIGGER %I',n); END $x$"),
          ('disable-parent-ri',"DO $x$ DECLARE n name; BEGIN SELECT tgname INTO n FROM pg_trigger WHERE tgrelid='public.mixer_browser_sessions'::regclass AND tgisinternal AND tgtype=9 LIMIT 1; EXECUTE format('ALTER TABLE public.mixer_browser_sessions DISABLE TRIGGER %I',n); END $x$"),
          ('extra-incoming-fk','CREATE TABLE public.representation_incoming(id text REFERENCES public.mixer_authz_principals(id))'),
          ('extra-policy','CREATE POLICY representation_extra ON public.mixer_authz_profiles FOR SELECT TO PUBLIC USING (true)'),
          ('alter-policy','ALTER POLICY scoped_lock ON public.mixer_authz_profiles WITH CHECK (true)'),
          ('grant-table-update','GRANT UPDATE ON public.mixer_browser_sessions TO browser_writer'),
          ('grant-immutable-column','GRANT UPDATE(id) ON public.mixer_browser_sessions TO browser_writer'),
          ('grant-public','GRANT SELECT ON public.mixer_browser_sessions TO PUBLIC'),
          ('grant-extra-role','GRANT SELECT ON public.mixer_browser_sessions TO representation_extra'),
          ('grant-option','GRANT SELECT ON public.mixer_browser_sessions TO browser_writer WITH GRANT OPTION'),
          ('alter-default','ALTER TABLE public.mixer_authz_profiles ALTER COLUMN state_revision SET DEFAULT 2'),
          ('drop-default','ALTER TABLE public.mixer_browser_oidc_attempts ALTER COLUMN ciphertext_version DROP DEFAULT'),
          ('extra-browser-relation','CREATE SCHEMA representation_escape; CREATE VIEW representation_escape.mixer_browser_shadow AS SELECT 1 AS n'),
          ('disable-rls','ALTER TABLE public.mixer_browser_sessions NO FORCE ROW LEVEL SECURITY'),
          ('check-noinherit','ALTER TABLE public.mixer_browser_sessions ADD CONSTRAINT representation_noinherit CHECK (true) NO INHERIT'),
          ('drop-partial-index','DROP INDEX public.mixer_browser_one_attempt'),
          ('alter-check',"ALTER TABLE public.mixer_browser_sessions DROP CONSTRAINT mixer_browser_sessions_status_check; ALTER TABLE public.mixer_browser_sessions ADD CHECK(status IN ('preauth','active','revoked','expired','extra'))"),
        ]
        if major==17: mutations.append(('grant-maintain','GRANT MAINTAIN ON public.mixer_browser_sessions TO browser_writer'))
        results=[]
        for name,mutation in mutations:
            _,output=run('mutation-'+name,db,data='BEGIN;\n'+mutation+';\n'+sql+'\nROLLBACK;')
            attacked=json.loads(output);different=canonical(attacked)!=frozen
            results.append({'name':name,'detected':different,'counts':{f:len(attacked[f]) for f in CAPS},'sha256':hashlib.sha256(output.encode()).hexdigest()})
            if not different: raise AssertionError('mutation undetected: '+name)
        _,after_output=run('restored-baseline',db,data=sql)
        receipt['rollback_restored_baseline']=canonical(json.loads(after_output))==frozen
        if not receipt['rollback_restored_baseline']: raise AssertionError('rollback baseline changed')
        write(out/'mutation-results.json',results);receipt['mutations_detected']=len(results)
        # Automatic diagnostic names are intentionally absent from the comparison oracle.
        _,renamed=run('automatic-name-control',db,data='BEGIN; ALTER TABLE public.mixer_browser_sessions RENAME CONSTRAINT mixer_browser_sessions_pkey TO renamed_automatic_key;\n'+sql+'\nROLLBACK;')
        receipt['automatic_rename_equivalent']=canonical(json.loads(renamed))==frozen
        if not receipt['automatic_rename_equivalent']: raise AssertionError('automatic name incorrectly treated as authority')
        receipt['passed']=True
    except Exception as e:
        receipt['failure']=type(e).__name__+': '+str(e)
    finally:
        if major==17 and scratch:
            if started and (scratch/'data/postmaster.pid').exists():
                run('stop',[PG/'pg_ctl','-D',scratch/'data','-m','immediate','-w','stop'],check=False)
            receipt['cleanup']['owned_server_stopped']=not (scratch/'data/postmaster.pid').exists()
            if receipt['cleanup']['owned_server_stopped']: shutil.rmtree(scratch)
            receipt['cleanup']['owned_scratch_removed']=not scratch.exists()
        elif major==16 and container:
            run('server-logs',['docker','logs',container],check=False)
            run('stop',['docker','stop','--timeout','5',container],check=False)
            code,_=run('absence',['docker','container','inspect',container],check=False)
            receipt['cleanup']['owned_container_absent']=code!=0
        receipt['source_changes_during_run']=[rel for rel,h in locals().get('manifest',{}).items() if sha(ROOT/rel)!=h]
        receipt['dependency_changes_during_run']=[rel for rel,h in locals().get('beams',{}).items() if sha(ROOT/rel)!=h]
        receipt['success']=receipt.get('passed',False) and all(receipt['cleanup'].values()) and not receipt['source_changes_during_run'] and not receipt['dependency_changes_during_run']
        receipt['outputs_sha256']={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and not str(p.relative_to(out)).startswith('inputs/')}
        receipt['finished_utc']=dt.datetime.now(dt.timezone.utc).isoformat();write(out/'receipt.json',receipt)
        print(str(out.relative_to(ROOT)));print(json.dumps({k:receipt.get(k) for k in ['success','failure','counts','semantic_methods_passed','mutations_detected','cleanup']}))
    return 0 if receipt['success'] else 1

if __name__=='__main__': raise SystemExit(main())
