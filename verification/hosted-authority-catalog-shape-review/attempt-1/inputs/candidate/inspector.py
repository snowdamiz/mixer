"""Bounded standalone inspector; never installs into or authorizes the product.

Selection is explicit in run.py; observation cannot update expected bytes.
All raw entries are checked before OID-only transport fields are removed. Lists
remain multisets with preserved multiplicity, including internal FK triggers.
"""
import copy, hashlib, json, pathlib
from raw_validation import validate_raw
HERE=pathlib.Path(__file__).resolve().parent
LEGACY=(HERE/'frozen/catalog.sql').read_text()
ENFORCEMENT=(HERE/'enforcement.sql').read_text()
SESSION="""SELECT jsonb_build_object('session_user',session_user,'current_user',current_user,'role',current_setting('role'),'database',current_database(),'session_replication_role',current_setting('session_replication_role'),'row_security',current_setting('row_security'),'default_transaction_isolation',current_setting('default_transaction_isolation'),'transaction_isolation',current_setting('transaction_isolation'),'transaction_read_only',current_setting('transaction_read_only'))"""
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(x):return hashlib.sha256(x).hexdigest()
def decode(value):
    def pairs(items):
        out={}
        for key,value in items:
            if key in out:raise ValueError('duplicate JSON key: '+key)
            out[key]=value
        return out
    def constant(value):raise ValueError('non-JSON numeric value: '+value)
    return json.loads(value,object_pairs_hook=pairs,parse_constant=constant)
def inspect(admin,fresh):
    return {'legacy':decode(admin.one(LEGACY)),'enforcement':decode(admin.one(ENFORCEMENT)),'fresh_session':decode(fresh.one(SESSION))}
def fail(message):raise ValueError(message)
def exact_keys(value,keys,where):
    if type(value) is not dict or set(value)!=set(keys):fail('malformed keys: '+where)
def oid(value,where):
    if type(value) is not int or value<0:fail('malformed OID: '+where)
def normalize(raw):
    validate_raw(raw)
    exact_keys(raw,['legacy','enforcement','fresh_session'],'root')
    if type(raw['legacy']) is not dict or type(raw['fresh_session']) is not dict:fail('malformed root values')
    x=copy.deepcopy(raw);e=x['enforcement']
    templates={
      'relations':'oid identity kind persistence replica_identity',
      'constraints':'oid identity relation type validated deferrable initially_deferred no_inherit local inheritance_count parent_oid parent_identity definition',
      'indexes':'oid identity relation valid ready live immediate unique primary exclusion nulls_not_distinct definition',
      'triggers':'oid name relation_oid relation function_oid function_identity enabled internal event_timing_bits deferrable initially_deferred constraint_oid constraint_identity referenced_relation_oid referenced_relation constraint_index_oid constraint_index parent_oid parent_identity argument_count argument_hex columns when old_table new_table definition',
      'parameter_acl':'oid parameter acl entries',
      'parameter_effective':'subject parameter context registered selected_set set alter_system',
      'parameter_public':'parameter context registered selected_set set alter_system',
      'role_config':'role config',
      'startup_defaults':'database_oid database role_oid role config'}
    exact_keys(e,templates,'enforcement')
    for group,keys in templates.items():
        if type(e[group]) is not list:fail('malformed list: '+group)
        seen=set()
        for row in e[group]:
            exact_keys(row,keys.split(),group)
            for k in row:
                if k=='oid' or k.endswith('_oid'):oid(row[k],group+'.'+k)
            if 'oid' in row:
                if row['oid']==0 or row['oid'] in seen:fail('duplicate/zero raw OID: '+group)
                seen.add(row['oid'])
            for flag in ['validated','deferrable','initially_deferred','no_inherit','local','valid','ready','live','immediate','unique','primary','exclusion','nulls_not_distinct','internal','registered','selected_set','set','alter_system']:
                if flag in row and type(row[flag]) is not bool:fail('malformed flag: '+group+'.'+flag)
            for ref,identity in [('parent_oid','parent_identity'),('constraint_oid','constraint_identity'),('referenced_relation_oid','referenced_relation'),('constraint_index_oid','constraint_index')]:
                if ref in row and bool(row[ref])!=(row[identity] is not None):fail('unresolved association: '+group+'.'+identity)
            if group=='triggers':
                if not row['relation_oid'] or not row['function_oid']:fail('missing trigger association')
                if row['internal']:
                    if row['constraint_identity'] is None:fail('unselected internal trigger without constraint')
                    # Generated FK names and their occurrence in deparsed DDL contain
                    # fresh-cluster OIDs. All semantic associations and flags remain.
                    del row['name'];del row['definition']
            for key in list(row):
                if key=='oid' or key.endswith('_oid'):del row[key]
            if group=='parameter_acl' and type(row['entries']) is list:row['entries'].sort(key=canonical)
        e[group].sort(key=canonical)
    if type(x['legacy'].get('memberships')) is list:x['legacy']['memberships'].sort(key=canonical)
    return x
def validate(raw,expected):
    observed=normalize(raw)
    # Exact structural equality preserves primitive types (bool != int via JSON),
    # order-independent catalog lists, and every duplicate entry's multiplicity.
    if canonical(observed)!=canonical(expected):
        changed=[key for key in observed if canonical(observed[key])!=canonical(expected.get(key))]
        fail('selected authority mismatch: '+','.join(changed))
    return observed
def safe_selection(raw):
    x=normalize(raw);e=x['enforcement'];c=x['legacy'];s=x['fresh_session']
    assert len(e['relations'])==14 and len(e['constraints'])==89 and len(e['indexes'])==26 and len(e['triggers'])==74
    assert all(r['kind']=='r' and r['persistence']=='p' and r['replica_identity']=='d' for r in e['relations'])
    assert all(r['enabled']=='O' for r in e['triggers'])
    assert all(r['validated'] and not r['deferrable'] and not r['initially_deferred'] for r in e['constraints'])
    assert all(r['valid'] and r['ready'] and r['live'] and r['immediate'] for r in e['indexes'])
    assert not e['parameter_acl'] and not e['startup_defaults']
    assert all(not r['alter_system'] and not(r['selected_set'] and r['set']) for group in ['parameter_effective','parameter_public'] for r in e[group])
    assert e['role_config']==[{'role':'mixer_hosted_runtime','config':None}]
    assert s=={'session_user':'mixer_hosted_runtime','current_user':'mixer_hosted_runtime','role':'none','database':'authority_contract','session_replication_role':'origin','row_security':'on','default_transaction_isolation':'read committed','transaction_isolation':'read committed','transaction_read_only':'off'}
    assert c['runtime_capabilities']=={'database_create':False,'database_temp':False,'public_create':False,'authz_create':False,'reachable':[]}
    return x
