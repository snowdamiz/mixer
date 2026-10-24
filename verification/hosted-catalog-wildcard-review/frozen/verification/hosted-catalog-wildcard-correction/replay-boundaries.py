#!/usr/bin/env python3
"""Deterministic raw-input matrix; never starts or modifies PostgreSQL.

The original 126 input mutations are replayed with an explicit new oracle:
the historical 21 malformed admissions must now reject; the 18 portable OIDs
still pass. Additional tests call raw validation directly, so exact selected
comparison cannot conceal a missing raw check. Synthetic valid unselected
shapes must pass raw validation and still fail selected comparison.
"""
import argparse, copy, datetime, gzip, hashlib, json, os, pathlib, sys
sys.dont_write_bytecode = True
HERE = pathlib.Path(os.environ.get('MIXER_SHAPE_PACKET', pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(HERE / 'candidate'))
from inspector import validate, normalize, decode, canonical
from raw_validation import validate_raw


def sha(value):
    return hashlib.sha256(value).hexdigest()


def load(path):
    path = pathlib.Path(path)
    return decode(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())


def outcome(fn):
    try:
        fn()
        return True, None
    except ValueError as exc:
        return False, str(exc)


def execute():
    original_path = HERE / 'inputs/verification/hosted-authority-catalog-review/attempt-2/domain-probes.json'
    source_path = HERE / 'inputs/verification/hosted-authority-catalog-review/attempt-2/independent/observations/001.json.gz'
    raw = load(source_path)['raw']; expected = load(HERE / 'selected-expected.json')
    original = load(original_path)
    validate(raw, expected)
    old = []
    for i, c in enumerate(original['cases']):
        other = copy.deepcopy(raw); rows = other['enforcement'][c['group']]
        if c['label'] == 'required nonempty internal text':
            row = next(r for r in rows if r['internal'])
        elif c['label'] == 'nonzero trigger association OID':
            row = next(r for r in rows if r['internal'] and bool(r[c['field']]))
        else:
            row = rows[0]
        row[c['field']] = c['value']
        raw_valid, raw_error = outcome(lambda: validate_raw(other))
        admitted, error = outcome(lambda: validate(other, expected))
        old.append({'index':i, 'original':c, 'changed_oracle': 'reject historical malformed admission' if c['contract_gap'] else 'preserve prior oracle',
                    'expected_admitted':c['domain_valid'], 'raw_valid':raw_valid, 'raw_error':raw_error,
                    'admitted':admitted, 'rejection':error, 'passed':admitted == c['domain_valid'] and raw_valid == c['domain_valid']})

    # These rows cover nonempty raw shapes absent from the safe selected state.
    whole = copy.deepcopy(raw)
    whole['enforcement']['parameter_acl'] = [{'oid':4294967295, 'parameter':'review.setting', 'acl':'{PUBLIC=s/postgres}',
        'entries':[{'grantor':'postgres', 'grantee':'PUBLIC', 'privilege':'SET', 'grantable':False}]}]
    whole['enforcement']['startup_defaults'] = [{'database_oid':4294967295, 'database':'authority_contract',
        'role_oid':0, 'role':'*', 'config':['row_security=on']}]
    validate_raw(whole)
    added = []
    def probe(label, change, raw_valid=False, admission=False):
        other = copy.deepcopy(whole); change(other)
        before = canonical(other)
        valid, raw_error = outcome(lambda: validate_raw(other))
        admitted, error = outcome(lambda: validate(other, expected))
        unchanged = canonical(other) == before
        added.append({'label':label, 'expected_raw_valid':raw_valid, 'expected_admitted':admission,
                      'raw_valid':valid, 'raw_error':raw_error, 'admitted':admitted, 'rejection':error,
                      'raw_input_unchanged':unchanged, 'passed':valid == raw_valid and admitted == admission and unchanged})
    def change_field(group, field, value):
        return lambda x:x['enforcement'][group][0].__setitem__(field, copy.deepcopy(value))
    # Every group, every required field, all top-level and row shape boundaries.
    probe('valid nonselected ACL/default shapes remain rejected by exact selection', lambda x:None, True)
    for root in ['legacy', 'enforcement', 'fresh_session']:
        probe('missing root ' + root, lambda x,k=root:x.pop(k))
        for value in [None, [], False, 0, '']:
            probe('root type ' + root + ' ' + repr(value), lambda x,k=root,v=value:x.__setitem__(k,v))
    probe('unknown root key', lambda x:x.update(extra=None))
    probe('unknown enforcement group', lambda x:x['enforcement'].update(extra=[]))
    for group, rows in whole['enforcement'].items():
        probe('missing group ' + group, lambda x,g=group:x['enforcement'].pop(g))
        for value in [None, {}, False, 1, '']:
            probe('group array type ' + group + ' ' + repr(value), lambda x,g=group,v=value:x['enforcement'].__setitem__(g,v))
        for value in [None, [], False, 1, '']:
            probe('row object type ' + group + ' ' + repr(value), lambda x,g=group,v=value:x['enforcement'][g].__setitem__(0,v))
        probe('unknown row key ' + group, lambda x,g=group:x['enforcement'][g][0].update(extra=None))
        for field, value in rows[0].items():
            probe('missing field ' + group + '.' + field, lambda x,g=group,f=field:x['enforcement'][g][0].pop(f))
            # Object/array values are invalid for every primitive field. Nested
            # fields have separate complete cases below; nullability is explicit.
            if field not in ('entries', 'config', 'parent_identity'):
                for invalid in [{}, []]:
                    probe('primitive shape ' + group + '.' + field + ' ' + repr(invalid), change_field(group,field,invalid))
            if type(value) is bool:
                for invalid in [0, 1, None, 'true']:
                    probe('bool type ' + group + '.' + field + ' ' + repr(invalid), change_field(group,field,invalid))
            elif type(value) is str:
                for invalid in [False, 0, 1.0, '\x00', '\ud800']:
                    probe('text type/encoding ' + group + '.' + field + ' ' + repr(invalid), change_field(group,field,invalid))
                if field not in ('argument_hex', 'columns'):
                    probe('required text empty ' + group + '.' + field, change_field(group,field,''))
            elif type(value) is int:
                for invalid in [True, 1.0, '1', -1, None, 4294967296]:
                    probe('integer type ' + group + '.' + field + ' ' + repr(invalid), change_field(group,field,invalid))
    for field in whole['fresh_session']:
        probe('missing session ' + field, lambda x,f=field:x['fresh_session'].pop(f))
        for value in [None, {}, [], False, 0, '', '\x00', '\ud800']:
            probe('session text ' + field + ' ' + repr(value), lambda x,f=field,v=value:x['fresh_session'].__setitem__(f,v))
    probe('unknown session field', lambda x:x['fresh_session'].update(extra='x'))
    # Optional OIDs and associations cannot disappear into normalized state.
    for group, field, identity in [('constraints','parent_oid','parent_identity'),
        ('triggers','parent_oid','parent_identity'), ('triggers','constraint_oid','constraint_identity'),
        ('triggers','referenced_relation_oid','referenced_relation'), ('triggers','constraint_index_oid','constraint_index')]:
        probe('nonzero unresolved ' + group + '.' + field, lambda x,g=group,f=field,i=identity:x['enforcement'][g][0].update({f:1,i:None}))
        resolved = {'relation':'mixer_authz.principals','name':'parent'} if group == 'triggers' and identity == 'parent_identity' else 'mixer_authz.principals/parent'
        probe('zero resolved ' + group + '.' + field, lambda x,g=group,f=field,i=identity,v=resolved:x['enforcement'][g][0].update({f:0,i:v}))
        for value in [4294967296, True, 1.0, '0', None, -1]:
            probe('optional OID domain ' + group + '.' + field + ' ' + repr(value), change_field(group,field,value))
    for group in ['relations','constraints','indexes','triggers','parameter_acl']:
        if len(whole['enforcement'][group]) > 1:
            probe('duplicate raw OID ' + group, lambda x,g=group:x['enforcement'][g][1].update(oid=x['enforcement'][g][0]['oid']))
        else:
            probe('duplicate raw OID ' + group, lambda x,g=group:x['enforcement'][g].append(copy.deepcopy(x['enforcement'][g][0])))
    for field in ['database','role']:
        for oid, identity in [(0,None),(0,'named'),(1,None),(1,'*')]:
            probe('startup wildcard association ' + field + ' ' + repr((oid,identity)), lambda x,f=field,o=oid,v=identity:x['enforcement']['startup_defaults'][0].update({f+'_oid':o,f:v}), raw_valid=(oid == 1 and identity == '*'))
    for group in ['parameter_effective','parameter_public']:
        probe('registered context absent ' + group, lambda x,g=group:x['enforcement'][g][0].update(context=None))
        probe('unregistered context resolved ' + group, lambda x,g=group:x['enforcement'][g][0].update(registered=False,selected_set=True))
        probe('unregistered selected_set false ' + group, lambda x,g=group:x['enforcement'][g][0].update(registered=False,context=None,selected_set=False))
        probe('unregistered valid raw parameter ' + group, lambda x,g=group:x['enforcement'][g][0].update(registered=False,context=None,selected_set=True),True)
    # Nested ACL, parent and settings values: unknown/missing keys and leaf types.
    acl = whole['enforcement']['parameter_acl'][0]['entries'][0]
    for value in [{}, False, 1, 'x', [None], [[]], [False]]:
        probe('ACL entries shape ' + repr(value), change_field('parameter_acl','entries',value))
    for value in [None, []]:
        probe('nullable ACL entries '+repr(value),change_field('parameter_acl','entries',value),True)
    probe('nullable ACL text',change_field('parameter_acl','acl',None),True)
    for field in acl:
        probe('ACL missing leaf ' + field, lambda x,f=field:x['enforcement']['parameter_acl'][0]['entries'][0].pop(f))
        for value in [None, {}, [], 0, '']:
            probe('ACL leaf type ' + field + ' ' + repr(value), lambda x,f=field,v=value:x['enforcement']['parameter_acl'][0]['entries'][0].__setitem__(f,v))
    probe('ACL unknown key', lambda x:x['enforcement']['parameter_acl'][0]['entries'][0].update(extra='x'))
    probe('ACL unknown privilege', lambda x:x['enforcement']['parameter_acl'][0]['entries'][0].update(privilege='SELECT'))
    for group in ['role_config','startup_defaults']:
        for value in [{}, False, 1, '', [None], [{}], [[]], [False], [0], [''], ['row_security'], ['=on'], ['a=\x00'], ['a=\ud800']]:
            probe('config shape ' + group + ' ' + repr(value), change_field(group,'config',value))
        for value in [None, [], ['application_name='], ['row_security=on','row_security=on']]:
            probe('config valid preserves entries ' + group + ' ' + repr(value), change_field(group,'config',value),True)
    for value in [{}, [], False, 1, '', {'relation':'mixer_authz.principals'}, {'name':'parent'},
                  {'relation':'mixer_authz.principals','name':'parent','extra':0}, {'relation':None,'name':'parent'},
                  {'relation':'','name':'parent'}, {'relation':'mixer_authz.principals','name':None},
                  {'relation':'mixer_authz.principals','name':'x'*64}]:
        probe('parent nested shape ' + repr(value), lambda x,v=value:x['enforcement']['triggers'][0].update(parent_oid=1,parent_identity=v))
    probe('valid resolved parent nested object', lambda x:x['enforcement']['triggers'][0].update(parent_oid=1,parent_identity={'relation':'mixer_authz.principals','name':'parent'}),True)
    for field in ['old_table','new_table']:
        for value in ['', {}, [], False, 0, 'x'*64, 'é'*32, '\x00', '\ud800']:
            probe('nullable identifier ' + field + ' ' + repr(value),change_field('triggers',field,value))
        probe('valid nullable identifier ' + field,change_field('triggers',field,'é'*31+'x'),True)
    for field in ['name','definition']:
        for value in ['\x00','\ud800']:
            probe('ignored internal text encoding '+field+' '+repr(value),change_field('triggers',field,value))
    for value in ['x'*64,'é'*32]:
        probe('ignored internal identifier byte overflow '+repr(value),change_field('triggers','name',value))
    for value in ['x'*63,'é'*31+'x']:
        probe('internal identifier exact byte bound '+repr(value),change_field('triggers','name',value),True)
    for value in ['harmless portable internal deparser text',' ']:
        probe('valid ignored internal definition '+repr(value),change_field('triggers','definition',value),True)
    for field in ['inheritance_count']:
        for value in [32768, True, 1.0, None]:
            probe('int16 constraint '+repr(value),change_field('constraints',field,value))
    for field in ['argument_count','event_timing_bits']:
        for value in [32768, True, 1.0, None]:
            probe('int16 trigger '+field+' '+repr(value),change_field('triggers',field,value))
    for value in [0, 1, 2, 3, 66, 70, 128, 32767, 33, 65, 97]:
        probe('invalid trigger bit combination '+str(value),change_field('triggers','event_timing_bits',value))
    for value in [4,5,6,9,17,20,28,32,36,69]:
        probe('valid unselected trigger bit combination '+str(value),change_field('triggers','event_timing_bits',value),True)
    for value in [None, False, 0, {}, [], '0', 'AA', 'gg', '0x00']:
        probe('argument hex domain '+repr(value),change_field('triggers','argument_hex',value))
    for count, encoded in [(0,'00'),(1,''),(1,'61'),(2,'6100')]:
        probe('argument count terminator '+repr((count,encoded)),lambda x,c=count,h=encoded:x['enforcement']['triggers'][0].update(argument_count=c,argument_hex=h))
    for count, encoded in [(1,'00'),(1,'6100'),(2,'61006200')]:
        probe('valid argument count terminator '+repr((count,encoded)),lambda x,c=count,h=encoded:x['enforcement']['triggers'][0].update(argument_count=c,argument_hex=h),True)
    for value in [None,False,0,{},[],'0','-1','32768','1.0','1,2','1  2',' 1','1 ']:
        probe('attribute vector domain '+repr(value),change_field('triggers','columns',value))
    for value in ['1','1 2','32767']:
        probe('valid attribute vector '+repr(value),change_field('triggers','columns',value),True)
    for group, field, invalid in [('relations','kind','x'),('relations','persistence','x'),('relations','replica_identity','x'),('constraints','type','xX'),('triggers','enabled','x')]:
        probe('enum domain '+group+'.'+field,change_field(group,field,invalid))
    # Multiplicity is not deduplicated even when OIDs and ignored names differ.
    for group in whole['enforcement']:
        def duplicate(x,g=group):
            row=copy.deepcopy(x['enforcement'][g][0])
            if 'oid' in row:
                row['oid']=4294967294
            x['enforcement'][g].append(row)
        probe('semantic duplicate retained '+group,duplicate,group != 'triggers')
    # Legacy raw nested structure is also checked before normalization.
    for change,label in [(lambda x:x['legacy'].update(extra=0),'unknown legacy key'),
        (lambda x:x['legacy']['tables'][0]['columns'][0].update(extra=0),'unknown legacy column key'),
        (lambda x:x['legacy']['roles'][0].update(login=1),'legacy bool integer'),
        (lambda x:x['legacy']['functions'][0].update(config=[None]),'legacy config nested null'),
        (lambda x:x['legacy']['runtime_capabilities'].update(reachable=[{}]),'legacy nested reachable object')]:
        probe(label,change)
    # Decode the actual transport: duplicate keys must reject at every nesting.
    transport=[]
    for label,value in [('root','{"legacy":{},"legacy":{}}'),('row','{"row":{"oid":1,"oid":2}}'),
        ('ACL','{"entries":[{"grantor":"a","grantor":"b"}]}'),('parent','{"parent":{"name":"a","name":"b"}}'),
        ('session','{"fresh_session":{"session_user":"a","session_user":"b"}}'),
        ('NaN','{"x":NaN}'),('Infinity','{"x":Infinity}'),('-Infinity','{"x":-Infinity}')]:
        valid,error=outcome(lambda v=value:decode(v))
        transport.append({'label':label,'input':value,'admitted':valid,'rejection':error,'passed':not valid})
    # Actual selected baseline portability controls do not include synthetic ACLs.
    portable=[]
    for label,change in [
        ('63-byte internal identifier',lambda x:next(r for r in x['enforcement']['triggers'] if r['internal']).update(name='é'*31+'x')),
        ('nonempty internal deparser text',lambda x:next(r for r in x['enforcement']['triggers'] if r['internal']).update(definition='different harmless internal formatting')),
        ('list order retained as multiset',lambda x:[rows.reverse() for rows in x['enforcement'].values()])]:
        other=copy.deepcopy(raw);change(other);admitted,error=outcome(lambda:validate(other,expected))
        portable.append({'label':label,'admitted':admitted,'rejection':error,'passed':admitted})
    result={'schema':1,'scope':'copied raw-input model only, separate from actual PostgreSQL runtime evidence',
        'original_boundary_source_sha256':sha(original_path.read_bytes()),'raw_source_sha256':sha(source_path.read_bytes()),
        'expected_sha256':sha((HERE/'selected-expected.json').read_bytes()),
        'original_126':{'total':len(old),'passed':sum(c['passed'] for c in old),'rejected':sum(not c['admitted'] for c in old),
                        'historical_21_now_rejected':sum(c['original']['contract_gap'] and not c['admitted'] for c in old),
                        'portable_18_admitted':sum(c['original']['domain_valid'] and c['admitted'] for c in old),'cases':old},
        'added_whole_shape':{'total':len(added),'passed':sum(c['passed'] for c in added),'raw_invalid_rejected':sum(not c['expected_raw_valid'] and not c['raw_valid'] for c in added),
                             'valid_unselected_raw_controls':sum(c['expected_raw_valid'] and c['raw_valid'] and not c['admitted'] for c in added),'cases':added},
        'strict_transport':{'total':len(transport),'passed':sum(c['passed'] for c in transport),'cases':transport},
        'selected_portability':{'total':len(portable),'passed':sum(c['passed'] for c in portable),'cases':portable}}
    result['passed']=all(c['passed'] for c in old+added+transport+portable)
    return result


if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args()
    out=pathlib.Path(args.out);out.mkdir(parents=True,exist_ok=False)
    result=execute();result['observed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();result['argv']=sys.argv
    result['script_sha256']=sha(pathlib.Path(__file__).read_bytes())
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:{a:b for a,b in v.items() if a!='cases'} if isinstance(v,dict) else v for k,v in result.items()},indent=2))
    sys.exit(0 if result['passed'] else 1)
