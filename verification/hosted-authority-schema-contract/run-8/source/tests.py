#!/usr/bin/env python3
"""Executable current-authority adversarial probes. All identities are synthetic."""
import ctypes, ctypes.util, datetime, getpass, hashlib, json, os, pathlib, subprocess, sys, threading, time, traceback
OUT=pathlib.Path(os.environ['MIXER_AUTHZ_OUT']);SOCK=os.environ['MIXER_AUTHZ_SOCKET'];SQLLOG=[];RESULTS=[]
libpath=str(pathlib.Path(subprocess.check_output(['pg_config','--libdir'],text=True).strip())/'libpq.5.dylib');pq=ctypes.CDLL(libpath)
def api(name,restype,args):
 f=getattr(pq,name);f.restype=restype;f.argtypes=args;return f
ptr=ctypes.c_void_p;cs=ctypes.c_char_p;ci=ctypes.c_int
connect=api('PQconnectdb',ptr,[cs]);status=api('PQstatus',ci,[ptr]);finish=api('PQfinish',None,[ptr]);execute=api('PQexec',ptr,[ptr,cs]);rs=api('PQresultStatus',ci,[ptr]);rows=api('PQntuples',ci,[ptr]);cols=api('PQnfields',ci,[ptr]);val=api('PQgetvalue',cs,[ptr,ci,ci]);err=api('PQresultErrorMessage',cs,[ptr]);field=api('PQresultErrorField',cs,[ptr,ci]);clear=api('PQclear',None,[ptr]);version=api('PQlibVersion',ci,[])
class DBError(Exception):
 def __init__(self,state,message):self.state=state;super().__init__(state+': '+message)
class DB:
 def __init__(self,user=None):
  self.user=user or getpass.getuser();self.c=connect(f'host={SOCK} dbname=authority_contract user={self.user}'.encode());assert status(self.c)==0
 def q(self,sql):
  t=time.monotonic();r=execute(self.c,sql.encode());item={'user':self.user,'sql':sql,'duration_seconds':time.monotonic()-t};SQLLOG.append(item)
  try:
   item['result_status']=rs(r)
   if item['result_status'] not in [1,2]:
    state=(field(r,ord('C')) or b'?????').decode();message=(err(r) or b'').decode();item.update(sqlstate=state,error=message);raise DBError(state,message)
   result=[[val(r,i,j).decode() for j in range(cols(r))] for i in range(rows(r))];item['rows']=result;return result
  finally:clear(r)
 def one(self,sql):return self.q(sql)[0][0]
 def close(self):
  if self.c:finish(self.c);self.c=None
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
def lit(s):return "'"+str(s).replace("'","''")+"'"
def record(typ,value):return f'jsonb_populate_record(NULL::mixer_authz.{typ},{lit(json.dumps(value,separators=(",",":")))}::jsonb)'
P='00000000-0000-0000-0000-000000000001';B='00000000-0000-0000-0000-000000000002';F='00000000-0000-0000-0000-000000000003';M='00000000-0000-0000-0000-000000000004';H='\\x'+'11'*32;R='\\x'+'22'*32;D='\\x'+'33'*32
ADMIN=DB();TABLES=[r[0] for r in ADMIN.q("SELECT tablename FROM pg_tables WHERE schemaname='mixer_authz' ORDER BY tablename")]
def seed(role='developer',expiry=None):
 ADMIN.q('TRUNCATE '+','.join('mixer_authz.'+x for x in TABLES)+' CASCADE')
 now=int(ADMIN.one('SELECT floor(extract(epoch FROM clock_timestamp()))'));exp=expiry or now+120
 ADMIN.q(f"""INSERT INTO mixer_authz.identity_trust_profiles VALUES('profile',1,true,'https://issuer.example','client','human',1);
 INSERT INTO mixer_authz.organizations VALUES('o','active',1),('other','active',1);
 INSERT INTO mixer_authz.principals VALUES('{P}','human','active',0,1,NULL);
 INSERT INTO mixer_authz.external_identity_bindings VALUES('{B}','profile','https://issuer.example','subject','client','human','{P}');
 INSERT INTO mixer_authz.credential_families VALUES('{F}','{B}','{P}','profile','active',0,1);
 INSERT INTO mixer_authz.credential_references VALUES('{B}',decode('{'11'*32}','hex'),'{F}','{P}','profile',{now-10},{exp});
 INSERT INTO mixer_authz.projects VALUES('o','p','active',1),('o','q','active',1),('other','p','active',1);
 INSERT INTO mixer_authz.applications VALUES('o','p','app','active',1);
 INSERT INTO mixer_authz.environments VALUES('o','p','app','dev','active','development',1),('o','p','app','prod','active','production',1);
 INSERT INTO mixer_authz.organization_authorization_heads VALUES('o',1),('other',1);
 INSERT INTO mixer_authz.project_authorization_heads VALUES('o','p',1),('o','q',1),('other','p',1);
 INSERT INTO mixer_authz.project_memberships VALUES('{M}','o','p','{P}',{lit(role)},'active',NULL,NULL,1,decode('{'44'*32}','hex'));""")
 return dict(profile_id='profile',profile_version=1,issuer='https://issuer.example',subject='subject',client_id='client',credential_sha256=H,issued_at=now-10,expires_at=exp,identity_class='human',scopes=['mixer.artifact.read','mixer.artifact.upload','mixer.audit.read'],authentication_completed_at=now),dict(action='artifact.upload',organization='o',project='p',app='app',environment='dev',platform='ios',runtime_sha256=R,manifest_sha256=D)
class Flow:
 def __init__(self,i,t,budget=5,isolation="READ COMMITTED"):
  self.i=i;self.t=t;self.db=DB('mixer_hosted_runtime');self.db.q("BEGIN;SET TRANSACTION ISOLATION LEVEL "+isolation+";SET LOCAL statement_timeout='5s';SET LOCAL lock_timeout='250ms'")
  self.db.q("SELECT set_config('mixer_authz.invocation_nonce',repeat('a',64),true),set_config('mixer_authz.deadline',(clock_timestamp()+interval "+lit(str(budget)+' seconds')+")::text,true)")
  self.x=json.loads(self.db.one("SELECT json_build_object('backend',pg_backend_pid(),'full_xid',pg_current_xact_id()::text,'database_name',current_database(),'runtime_role',session_user,'nonce',current_setting('mixer_authz.invocation_nonce'),'deadline',current_setting('mixer_authz.deadline'))"));self.a=None
 def call(self,name,a=None):
  args=[record('verified_identity_v1',self.i),record('target_v1',self.t)]
  if name!='lookup_admission':args.append(record('admission_v1',a or self.a))
  args.append(record('transaction_identity_v1',self.x))
  return json.loads(self.db.one('SELECT row_to_json(mixer_authz.'+name+'('+','.join(args)+'))'))
 def lookup(self):self.a=self.call('lookup_admission');return self.a
 def lock(self):self.a=self.call('lock_admission_rows');return self.a
 def decide(self):return self.call('decide_current')
 def close(self):self.db.q('ROLLBACK');self.db.close()
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
def deny(fn,state='42501'):
 try:fn()
 except DBError as e:assert e.state==state,(e.state,state);return
 raise AssertionError('unexpected allow')
def case(name,fn):
 t=time.monotonic()
 try:ob=fn();RESULTS.append({'name':name,'passed':True,'seconds':time.monotonic()-t,'observation':ob})
 except Exception as e:RESULTS.append({'name':name,'passed':False,'seconds':time.monotonic()-t,'error':repr(e),'traceback':traceback.format_exc()})
 finally:(OUT/'tests.json').write_text(json.dumps({'tests':RESULTS,'passed':sum(x['passed'] for x in RESULTS),'total':len(RESULTS)},indent=2)+'\n');(OUT/'sql-commands.json').write_text(json.dumps(SQLLOG,indent=2)+'\n')
def success(role,action):
 i,t=seed(role);t['action']=action
 if action=='audit.read':t.update(app=None,environment=None,platform=None,runtime_sha256=None,manifest_sha256=None)
 with Flow(i,t) as f:
  f.lookup();a=f.lock();d=f.decide();expected='allowed' if role in ['owner','administrator','developer'] or (action!='artifact.upload' and role in ['release_manager','viewer']) else 'forbidden';assert d['outcome']==expected;assert len(d['memberships'])==1;assert list(d['memberships'][0])==['lifecycle_id','role','revision'];return d
for role in ['owner','administrator','developer','release_manager','billing_manager','viewer']:
 for action in ['artifact.read','artifact.upload','audit.read']:case('role '+role+' '+action,lambda r=role,a=action:success(r,a))
def mutation(which,key,value,where='lookup'):
 i,t=seed();(i if which=='identity' else t)[key]=value
 with Flow(i,t) as f:
  if where=='lookup':deny(f.lookup)
  else:f.lookup();f.lock();deny(f.decide)
for key,value in [('profile_id','unknown'),('profile_version',2),('issuer','https://issuer.example/'),('subject','Subject'),('client_id','Client'),('credential_sha256','\\x'+'99'*32),('identity_class','service'),('issued_at',1.5),('issued_at','NaN'),('expires_at','Infinity'),('expires_at','-Infinity'),('authentication_completed_at',-1),('authentication_completed_at',9007199254740992),('authentication_completed_at',1.2),('scopes',['owner']),('scopes',['mixer.artifact.upload']*2),('scopes',[None]),('credential_sha256','\\x00')]:
 case('invalid identity '+key+' '+str(value),lambda k=key,v=value:mutation('identity',k,v,'decision' if k=='profile_version' else 'lookup'))
for key,value in [('action','release.publish'),('action',None),('organization','*'),('project',''),('app',None),('environment','*'),('platform','IOS'),('runtime_sha256','\\x00'),('manifest_sha256',None)]:case('invalid target '+key,lambda k=key,v=value:mutation('target',k,v))
def missing_scope():
 i,t=seed();i['scopes']=['mixer.artifact.read']
 with Flow(i,t) as f:f.lookup();f.lock();assert f.decide()['outcome']=='forbidden'
case('exact action scope intersection',missing_scope)
def state_change(sql,outcome=None):
 i,t=seed();ADMIN.q(sql)
 with Flow(i,t) as f:
  f.lookup();f.lock()
  if outcome:assert f.decide()['outcome']==outcome
  else:deny(f.decide)
for name,sql,outcome in [
 ('profile disabled',"UPDATE mixer_authz.identity_trust_profiles SET enabled=false,revision=2",None),
 ('principal disabled',"UPDATE mixer_authz.principals SET status='disabled',revision=2",None),
 ('principal cutoff',"UPDATE mixer_authz.principals SET valid_after=9007199254740991,revision=2",None),
 ('family revoked',"UPDATE mixer_authz.credential_families SET status='revoked',revision=2",None),
 ('family cutoff',"UPDATE mixer_authz.credential_families SET valid_after=9007199254740991,revision=2",None),
 ('denial absent-row fence',f"INSERT INTO mixer_authz.credential_denials SELECT binding_id,jti_sha256,accepted_expires_at,accepted_issued_at,accepted_expires_at+30,1,'revoked' FROM mixer_authz.credential_references",None),
 ('organization deleted',"UPDATE mixer_authz.organizations SET status='deleted',revision=2 WHERE organization='o'",'not_found'),
 ('project deleted',"UPDATE mixer_authz.projects SET status='deleted',revision=2 WHERE organization='o' AND project='p'",'not_found'),
 ('app deleted',"UPDATE mixer_authz.applications SET status='deleted',revision=2",'not_found'),
 ('environment deleted',"UPDATE mixer_authz.environments SET status='deleted',revision=2 WHERE environment='dev'",'not_found'),
 ('membership revoked',"UPDATE mixer_authz.project_memberships SET status='revoked',revision=2",'not_found'),
 ('membership future window',"UPDATE mixer_authz.project_memberships SET not_before=9007199254740990,revision=2",'not_found'),
 ('membership expired window',"UPDATE mixer_authz.project_memberships SET expires_at=1,revision=2",'not_found')]:case(name,lambda s=sql,o=outcome:state_change(s,o))
def org_binding(kind):
 i,t=seed();ADMIN.q("TRUNCATE mixer_authz.project_memberships");ADMIN.q(f"INSERT INTO mixer_authz.organization_memberships VALUES('{M}','o',{lit(kind)},'{P}','developer','active',NULL,NULL,1,decode('{'44'*32}','hex'))")
 with Flow(i,t) as f:f.lookup();f.lock();d=f.decide();assert d['outcome']==('allowed' if kind=='organization_wide' else 'not_found');return d
case('organization-wide explicit binding',lambda:org_binding('organization_wide'));case('organization-only no project grant',lambda:org_binding('organization_only'))

def duplicate_lifecycle_union():
 i,t=seed();ADMIN.q(f"INSERT INTO mixer_authz.organization_memberships VALUES('{M}','o','organization_wide','{P}','viewer','active',NULL,NULL,1,decode('{'44'*32}','hex'))")
 with Flow(i,t) as f:f.lookup();f.lock();d=f.decide();assert d['outcome']=='authorization_unavailable' and d['memberships']==[];return {'same_uuid_across_membership_tables':True,'closed_unavailable':True,'no_ambiguous_audit_witness':True}
case('duplicate lifecycle UUID across org-project union',duplicate_lifecycle_union)

def target_other_org():
 i,t=seed();t.update(organization='other')
 with Flow(i,t) as f:f.lookup();f.lock();assert f.decide()['outcome']=='not_found'
case('exact tenant ancestry cross organization',target_other_org)
def substituted(which,key,value):
 i,t=seed()
 with Flow(i,t) as f:
  f.lookup();f.lock();obj=f.a if which=='admission' else f.x;obj[key]=value;deny(f.decide)
for which,key,value in [('admission','principal_id','00000000-0000-0000-0000-000000000099'),('admission','family_id','00000000-0000-0000-0000-000000000099'),('admission','lock_statement_at','-infinity'),('admission','lock_statement_at','infinity'),('admission','profile_revision',2),('admission','project_revision',None),('transaction','backend',1),('transaction','full_xid','1'),('transaction','database_name','other'),('transaction','runtime_role','other'),('transaction','nonce','b'*64)]:case('substitution '+key,lambda w=which,k=key,v=value:substituted(w,k,v))
def target_substitution():
 i,t=seed()
 with Flow(i,t) as f:f.lookup();f.lock();f.t=dict(t,environment='prod');deny(f.decide)
case('exact live target cannot substitute',target_substitution)
def same_statement():
 i,t=seed()
 with Flow(i,t) as f:
  f.lookup();f.lock();a=dict(f.a,lock_statement_at=f.db.one('SELECT clock_timestamp()::text'))
  # Clock is prior to next statement, so directly invoke lock+decision in one statement instead.
  args=','.join([record('verified_identity_v1',i),record('target_v1',t),record('admission_v1',f.a),record('transaction_identity_v1',f.x)])
  deny(lambda:f.db.q('SELECT mixer_authz.decide_current('+record('verified_identity_v1',i)+','+record('target_v1',t)+',mixer_authz.lock_admission_rows('+args+'),'+record('transaction_identity_v1',f.x)+')'))
case('same-statement decision rejected',same_statement)
def repeatable_read():
 i,t=seed()
 with Flow(i,t,isolation='REPEATABLE READ') as f:deny(f.lookup)
case('repeatable-read transaction rejected',repeatable_read)
def clock_boundary(kind):
 i,t=seed()
 now=int(ADMIN.one('SELECT floor(extract(epoch FROM clock_timestamp()))'))
 if kind=='future-accepted':i['authentication_completed_at']=now+30
 elif kind=='future-denied':i['authentication_completed_at']=now+31
 elif kind=='old-denied':i['authentication_completed_at']=now-46
 with Flow(i,t) as f:
  f.lookup();f.lock()
  if kind=='future-accepted':assert f.decide()['outcome']=='allowed'
  else:deny(f.decide)
for k in ['future-accepted','future-denied','old-denied']:case('completion clock '+k,lambda k=k:clock_boundary(k))
def cardinality(count):
 i,t=seed();ADMIN.q('DROP INDEX mixer_authz.project_memberships_active_unique')
 try:
  for n in range(1,count):ADMIN.q(f"INSERT INTO mixer_authz.project_memberships VALUES('{n:08x}-1111-1111-1111-111111111111','o','p','{P}','viewer','active',NULL,NULL,1,decode('{'44'*32}','hex'))")
  with Flow(i,t) as f:f.lookup();f.lock();d=f.decide();assert d['outcome']==('allowed' if count==64 else 'authorization_unavailable');assert len(d['memberships'])==(64 if count==64 else 0);return {'owner_corruption_fixture_only':True,'count':count,'outcome':d['outcome']}
 finally:
  ADMIN.q('TRUNCATE mixer_authz.project_memberships');ADMIN.q("CREATE UNIQUE INDEX project_memberships_active_unique ON mixer_authz.project_memberships(principal_id,organization,project,role) WHERE status='active'")
case('bounded 64 membership control',lambda:cardinality(64));case('fetch65 overflow unavailable',lambda:cardinality(65))
def privilege(sql):
 with DB('mixer_hosted_runtime') as db:deny(lambda:db.q(sql),'42501')
for name,sql in [('direct authz select','SELECT * FROM mixer_authz.principals'),('direct authz insert',f"INSERT INTO mixer_authz.organization_authorization_heads VALUES('hidden',1)"),('direct revision update','UPDATE mixer_authz.identity_trust_profiles SET revision=2'),('direct delete','DELETE FROM mixer_authz.credential_denials'),('direct truncate','TRUNCATE mixer_authz.principals CASCADE'),('set schema owner','SET ROLE mixer_hosted_schema_owner'),('set resolver','SET ROLE mixer_hosted_authz_resolver'),('set writer','SET ROLE mixer_hosted_domain_writer'),('create schema','CREATE SCHEMA backdoor'),('create temp','CREATE TEMP TABLE backdoor(a int)'),('private helper','SELECT mixer_authz.finite_uint(1,0,2)'),('writer recheck entry','SELECT mixer_authz.recheck_current(NULL,NULL,NULL,NULL)')]:case('privilege '+name,lambda s=sql:privilege(s))
def guard(sql):seed();deny(lambda:ADMIN.q(sql),'23514')
for name,sql in [('profile reassignment',"UPDATE mixer_authz.identity_trust_profiles SET issuer='other',revision=2"),('principal class reassignment',"UPDATE mixer_authz.principals SET kind='service',revision=2"),('binding mutation',"UPDATE mixer_authz.external_identity_bindings SET subject='other'"),('reference mutation',"UPDATE mixer_authz.credential_references SET accepted_expires_at=1"),('revision skipped',"UPDATE mixer_authz.principals SET revision=3"),('hard deletion',"DELETE FROM mixer_authz.project_memberships")]:case('immutable guard '+name,lambda s=sql:guard(s))
def wait_for_block(victim,blocker):
 deadline=time.monotonic()+1
 while time.monotonic()<deadline:
  r=ADMIN.one(f"SELECT {blocker}=ANY(pg_blocking_pids({victim}))")
  if r=='t':return
  time.sleep(.005)
 raise AssertionError('actual expected database wait not observed')
def lock_order():
 i,t=seed();conditions=[('identity_trust_profiles',"profile_id='profile'"),('principals',f"principal_id='{P}'"),('credential_families',f"family_id='{F}'"),('organization_authorization_heads',"organization='o'"),('project_authorization_heads',"organization='o' AND project='p'")];blockers=[];observed=[]
 with Flow(i,t) as f:
  f.lookup()
  try:
   for table,where in conditions:
    b=DB();b.q('BEGIN');b.q(f'SELECT 1 FROM mixer_authz.{table} WHERE {where} FOR UPDATE');blockers.append(b)
   error=[]
   def locking():
    try:f.lock()
    except Exception as e:error.append(repr(e))
   thread=threading.Thread(target=locking);thread.start()
   for (table,_),b in zip(conditions,blockers):
    pid=int(b.one('SELECT pg_backend_pid()'));wait_for_block(f.x['backend'],pid);observed.append({'stage':table,'blocking_pid':pid,'wait_observed':True});b.q('COMMIT')
   thread.join(2);assert not thread.is_alive() and not error,error;assert f.decide()['outcome']=='allowed';return observed
  finally:
   for b in blockers:b.close()
case('actual five lock wait order and cardinality',lock_order)
def race_revocation_before():
 i,t=seed()
 with Flow(i,t) as f:
  f.lookup();b=DB();b.q('BEGIN');b.q("SELECT 1 FROM mixer_authz.identity_trust_profiles WHERE profile_id='profile' FOR SHARE");b.q(f"SELECT 1 FROM mixer_authz.principals WHERE principal_id='{P}' FOR SHARE");b.q(f"SELECT 1 FROM mixer_authz.credential_families WHERE family_id='{F}' FOR SHARE");b.q("SELECT 1 FROM mixer_authz.organization_authorization_heads WHERE organization='o' FOR SHARE");b.q("SELECT 1 FROM mixer_authz.project_authorization_heads WHERE organization='o' AND project='p' FOR UPDATE");b.q("UPDATE mixer_authz.project_memberships SET status='revoked',revision=2");b.q("UPDATE mixer_authz.project_authorization_heads SET revision=2 WHERE organization='o' AND project='p'");errors=[]
  def work():
   try:f.lock()
   except Exception as e:errors.append(repr(e))
  th=threading.Thread(target=work);th.start();wait_for_block(f.x['backend'],int(b.one('SELECT pg_backend_pid()')));b.q('COMMIT');b.close();th.join(2);assert not errors;d=f.decide();assert d['outcome']=='not_found' and d['project_revision']==2;return {'actual_wait':True,'committed_revocation_seen':True,'decision':d}
case('writer-before-admission fresh state after wait',race_revocation_before)
def race_revocation_after():
 i,t=seed()
 with Flow(i,t) as f:
  f.lookup();f.lock();assert f.decide()['outcome']=='allowed';b=DB();b.q('BEGIN');b.q("SET LOCAL lock_timeout='1s'");errors=[]
  def work():
   try:b.q("SELECT 1 FROM mixer_authz.project_authorization_heads WHERE organization='o' AND project='p' FOR UPDATE")
   except Exception as e:errors.append(repr(e))
  th=threading.Thread(target=work);th.start();wait_for_block(int(b.one('SELECT pg_backend_pid()')) if False else int(ADMIN.one("SELECT pid FROM pg_stat_activity WHERE query LIKE 'SELECT 1 FROM mixer_authz.project_authorization_heads%' AND wait_event_type='Lock' LIMIT 1")),f.x['backend']);f.db.q('ROLLBACK');th.join(2);assert not errors;b.q('ROLLBACK');b.close();return {'actual_wait':True,'admitted_operation_fences_later_writer':True}
case('admission-before-writer held shared lock fence',race_revocation_after)

def hidden_lock_row(table):
 i,t=seed();ADMIN.q('DROP POLICY resolver_lock ON mixer_authz.'+table)
 try:
  with Flow(i,t) as f:f.lookup();deny(f.lock)
 finally:ADMIN.q('CREATE POLICY resolver_lock ON mixer_authz.'+table+' FOR UPDATE TO mixer_hosted_authz_resolver USING(true) WITH CHECK(true)')
for tab in ['identity_trust_profiles','principals','credential_families','organization_authorization_heads','project_authorization_heads']:case('each lock asserts visible cardinality1 '+tab,lambda t=tab:hidden_lock_row(t))
def expiry_after_wait():
 # Align the short token near the next integral second, then observe an actual <=250ms DB lock wait.
 while True:
  wall=float(ADMIN.one('SELECT extract(epoch FROM clock_timestamp())'))
  if .60<wall%1<.70:break
  time.sleep(.01)
 exp=int(wall)+1;i,t=seed(expiry=exp)
 with Flow(i,t) as f:
  f.lookup();b=DB();b.q('BEGIN');b.q("SELECT 1 FROM mixer_authz.project_authorization_heads WHERE organization='o' AND project='p' FOR UPDATE");pid=int(b.one('SELECT pg_backend_pid()'))
  while float(ADMIN.one('SELECT extract(epoch FROM clock_timestamp())'))<exp-.09:time.sleep(.005)
  errors=[]
  def work():
   try:f.lock()
   except Exception as e:errors.append(repr(e))
  th=threading.Thread(target=work);th.start();wait_for_block(f.x['backend'],pid)
  while float(ADMIN.one('SELECT extract(epoch FROM clock_timestamp())'))<exp+.015:time.sleep(.005)
  b.q('COMMIT');b.close();th.join(1);assert not errors,errors;deny(f.decide);return {'actual_wait':True,'database_expiry':exp,'released_after_expiry':True,'no_domain_effects_exist_in_specimen':True}
case('actual wait crossing strict token expiry',expiry_after_wait)
def deadline_after_wait():
 i,t=seed()
 with Flow(i,t,budget=.12) as f:
  f.lookup();b=DB();b.q('BEGIN');b.q("SELECT 1 FROM mixer_authz.project_authorization_heads WHERE organization='o' AND project='p' FOR UPDATE");pid=int(b.one('SELECT pg_backend_pid()'));errors=[]
  def work():
   try:f.lock()
   except Exception as e:errors.append(repr(e))
  th=threading.Thread(target=work);th.start();wait_for_block(f.x['backend'],pid);time.sleep(.14);b.q('COMMIT');b.close();th.join(1);assert errors and '42501' in errors[0],errors;return {'actual_wait':True,'original_deadline_rejected_after_wait':True}
case('actual wait crossing original SQL deadline',deadline_after_wait)
def writer_no_locks():
 i,t=seed()
 ADMIN.q("CREATE SCHEMA fixture_writer")
 ADMIN.q("GRANT USAGE ON SCHEMA fixture_writer TO mixer_hosted_domain_writer,mixer_hosted_runtime")
 ADMIN.q("CREATE FUNCTION fixture_writer.recheck(i mixer_authz.verified_identity_v1,t mixer_authz.target_v1,a mixer_authz.admission_v1,x mixer_authz.transaction_identity_v1) RETURNS mixer_authz.decision_v1 LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog SET row_security=on AS 'SELECT mixer_authz.recheck_current(i,t,a,x)'")
 ADMIN.q('ALTER FUNCTION fixture_writer.recheck(mixer_authz.verified_identity_v1,mixer_authz.target_v1,mixer_authz.admission_v1,mixer_authz.transaction_identity_v1) OWNER TO mixer_hosted_domain_writer')
 try:
  with Flow(i,t) as f:
   f.lookup();f.lock();assert f.decide()['outcome']=='allowed'
   args=','.join([record('verified_identity_v1',i),record('target_v1',t),record('admission_v1',f.a),record('transaction_identity_v1',f.x)])
   # Already held actual authority locks; wrapper is fixture-only, not product surface.
   d=json.loads(f.db.one('SELECT row_to_json(fixture_writer.recheck('+args+'))'));assert d['outcome']=='allowed'
   definition=ADMIN.one("SELECT pg_get_functiondef('mixer_authz.recheck_current(mixer_authz.verified_identity_v1,mixer_authz.target_v1,mixer_authz.admission_v1,mixer_authz.transaction_identity_v1)'::regprocedure)")
   assert 'FOR SHARE' not in definition and 'lock_admission_rows(' not in definition
   return {'writer_definer_context_accepted':True,'no_lock_acquisition_in_recheck':True,'fixture_wrapper_removed':True}
 finally:ADMIN.q('DROP SCHEMA fixture_writer CASCADE')
case('writer recheck separate no lower-order acquisition',writer_no_locks)


def role_self_context():
 i,t=seed()
 with Flow(i,t) as f:f.db.q('SET ROLE mixer_hosted_runtime');deny(f.lookup)
case('SET ROLE self rejected by exact role context',role_self_context)
def forged_initial_admission():
 i,t=seed()
 with Flow(i,t) as f:
  f.lookup();a=dict(f.a,profile_revision=1,principal_revision=1,family_revision=1,organization_revision=1,project_revision=1,lock_statement_at='2000-01-01T00:00:00+00:00')
  b=DB();b.q('BEGIN');b.q("SELECT 1 FROM mixer_authz.project_authorization_heads WHERE organization='o' AND project='p' FOR UPDATE");pid=int(b.one('SELECT pg_backend_pid()'));res=[];errors=[]
  def work():
   try:res.append(f.call('decide_current',a))
   except Exception as e:errors.append(repr(e))
  th=threading.Thread(target=work);th.start();wait_for_block(f.x['backend'],pid);b.q('COMMIT');b.close();th.join(1);assert not errors and res[0]['outcome']=='allowed';return {'forged_composite_did_not_bypass_actual_shared_lock':True,'actual_wait':True}
case('forged admission still acquires actual lock',forged_initial_admission)

def internal_fresh_after_wait():
 # Test-only forged prior witness makes the outer decision statement start before writer commit.
 # The decision still takes actual locks; fresh VOLATILE internal queries must see the commit.
 i,t=seed()
 with Flow(i,t) as f:
  f.lookup();a=dict(f.a,profile_revision=1,principal_revision=1,family_revision=1,organization_revision=1,project_revision=2,lock_statement_at='2000-01-01T00:00:00+00:00')
  b=DB();b.q('BEGIN');b.q("SELECT 1 FROM mixer_authz.project_authorization_heads WHERE organization='o' AND project='p' FOR UPDATE");pid=int(b.one('SELECT pg_backend_pid()'));b.q("UPDATE mixer_authz.project_memberships SET status='revoked',revision=2");b.q("UPDATE mixer_authz.project_authorization_heads SET revision=2 WHERE organization='o' AND project='p'");res=[];errors=[]
  def work():
   try:res.append(f.call('decide_current',a))
   except Exception as e:errors.append(repr(e))
  th=threading.Thread(target=work);th.start();wait_for_block(f.x['backend'],pid);b.q('COMMIT');b.close();th.join(1);assert not errors,errors;assert res[0]['outcome']=='not_found' and res[0]['project_revision']==2;return {'outer_statement_started_before_commit':True,'actual_wait':True,'fresh_internal_query_saw_committed_revocation':True,'synthetic_prior_witness_not_capability':True}
case('VOLATILE internal current-state snapshot after wait',internal_fresh_after_wait)

def retention_guard():
 seed();deny(lambda:ADMIN.q("INSERT INTO mixer_authz.credential_denials SELECT binding_id,jti_sha256,accepted_expires_at,accepted_issued_at,accepted_expires_at+29,1,'revoked' FROM mixer_authz.credential_references"),'23514')
case('credential denial expiry+30 retention floor',retention_guard)
def profile_reenable():
 seed();ADMIN.q("UPDATE mixer_authz.identity_trust_profiles SET enabled=false,revision=2");deny(lambda:ADMIN.q("UPDATE mixer_authz.identity_trust_profiles SET enabled=true,revision=3"),'23514')
case('profile reenable requires higher version',profile_reenable)

CAT=(pathlib.Path(__file__).with_name('catalog.sql')).read_text()
def catalog():return json.loads(ADMIN.one(CAT))
def catalog_baseline():
 c=catalog();
 with DB('mixer_hosted_runtime') as rt:
  assert rt.one("SELECT session_user=current_user AND current_user='mixer_hosted_runtime' AND current_setting('role')='none'")=='t';assert json.loads(rt.one(CAT))==c
 assert c['runtime_owned_objects']==[] and c['runtime_creatable_schemas']==[];assert all(t['rls'] and t['force'] for t in c['tables']);assert all(not f['public_execute'] for f in c['functions']);assert len([f for f in c['functions'] if f['runtime_execute']])==3;assert len([f for f in c['functions'] if f['writer_execute']])==1;assert c['runtime_capabilities']=={'database_create':False,'database_temp':False,'public_create':False,'authz_create':False,'reachable':[]}
 typ=next(t for t in c['types'] if t['name']=='verified_identity_v1');assert all(f['type']=='numeric' for f in typ['fields'] if f['name'] in ['issued_at','expires_at','authentication_completed_at']);(OUT/'catalog.json').write_text(json.dumps(c,indent=2,sort_keys=True)+'\n');return {'functions':len(c['functions']),'tables':len(c['tables']),'types':len(c['types']),'all_force_rls':True,'public_execute':False}
case('exact complete catalog baseline',catalog_baseline)
BASE=catalog()
def drift(sql):
 ADMIN.q('BEGIN')
 try:ADMIN.q(sql);after=catalog();assert after!=BASE;return {'exact_manifest_rejects_drift':True}
 finally:ADMIN.q('ROLLBACK')
for name,sql in [('force rls',"ALTER TABLE mixer_authz.principals NO FORCE ROW LEVEL SECURITY"),('public helper execute',"GRANT EXECUTE ON FUNCTION mixer_authz.finite_uint(numeric,numeric,numeric) TO PUBLIC"),('search path',"ALTER FUNCTION mixer_authz.finite_uint(numeric,numeric,numeric) SET search_path=public"),('runtime bypass',"ALTER ROLE mixer_hosted_runtime BYPASSRLS"),('owner chain',"GRANT mixer_hosted_schema_owner TO mixer_hosted_runtime WITH INHERIT FALSE,SET TRUE"),('schema create',"GRANT CREATE ON SCHEMA mixer_authz TO mixer_hosted_runtime"),('database temp',"GRANT TEMP ON DATABASE authority_contract TO mixer_hosted_runtime"),('unknown table',"CREATE TABLE mixer_authz.unexpected(a integer)"),('extra helper',"CREATE FUNCTION mixer_authz.backdoor() RETURNS integer LANGUAGE sql AS 'SELECT 1'"),('unknown composite',"CREATE TYPE mixer_authz.unexpected_type AS(a integer)")]:case('catalog drift '+name,lambda s=sql:drift(s))
ADMIN.close();summary={'total':len(RESULTS),'passed':sum(x['passed'] for x in RESULTS),'failed':[x['name'] for x in RESULTS if not x['passed']],'libpq_path':libpath,'libpq_version':version()};(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary));sys.exit(0 if not summary['failed'] else 1)
