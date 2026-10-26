#!/usr/bin/env python3
"""Offline source-custody and lifetime-arithmetic verifier; no Rust execution."""
import copy
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
C3='verification/swift-cache-state-implementation/correction-3/'
SOURCE=C3+'source/library/cache_state.rs'
EXPECTED='0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8'
ROLES={'Candidate':(2048,0,2048),'Control':(6656,1280,8192),'IO':(1472,0,4096),'Metadata':(2400,0,4096),'Report':(4296,2896,8192),'Setup':(5168,256,12288),'Wire':(2616,256,3072)}
def require(value,message):
    if not value: raise ValueError(message)
def read(name): return json.loads((HERE/name).read_text())
def sha(data): return hashlib.sha256(data).hexdigest()
def inputs_check(document):
    for row in document['members']:
        data=(ROOT/row['path']).read_bytes()
        require(len(data)==row['bytes'] and sha(data)==row['sha256'],'input drift: '+row['path'])
def phases_check(document):
    require(document['fixed_role_union_bytes']==29344,'fixed union changed')
    require(document['reserved_bytes']==41984 and document['global_bytes']==65536,'cap changed')
    require(document['global_unassigned_margin_used']==0,'unassigned margin spent')
    require(document['whole_lifetime_proof_accepted'] is False and document['proposal_only'] is True,'acceptance overclaim')
    seen=set()
    for phase in document['phases']:
        require(phase['id'] not in seen,'duplicate phase')
        seen.add(phase['id'])
        names=[p['place'] for p in phase['added_places']]
        require(len(names)==len(set(names)),'aliased slot double allocation')
        for role,(old,addition,reserved) in ROLES.items():
            total=sum(p['bytes'] for p in phase['added_places'] if p['role']==role)
            require(total==phase['added_totals'][role],'sum mismatch')
            require(total<=addition,'added role exceeded: '+phase['id']+' '+role)
            require(phase['inherited_upper'][role]==old,'inherited role changed')
            require(phase['composed_upper'][role]==old+total and old+total<=reserved,'reservation exceeded')
    clears=[p for p in document['phases'] if p['id'].startswith('cleanup.anonymous128.')]
    require(len(clears)==16,'clear phase missing')
    for phase in clears:
        arrays=[p for p in phase['added_places'] if p['place'].startswith('anonymous128@')]
        require(len(arrays)==1 and arrays[0]['bytes']==128 and arrays[0]['role']=='Wire','sole clear source payload missing/duplicated')
        require(phase['added_totals']['Wire']==152,'Paid24 + anonymous128 subtotal changed')
    peaks={role:max(p['added_totals'][role] for p in document['phases']) for role in ROLES}
    require(peaks==document['added_role_peaks'],'peak drift')
    require(sum(old+add for old,add,_ in ROLES.values())==29344,'union arithmetic')
def templates_check(document):
    templates=document['templates']
    for template in templates.values():
        require(sum(p['bytes'] for p in template['places'])==template['conservative_phase_union_bytes'],'template sum mismatch')
        require(len({p['id'] for p in template['places']})==len(template['places']),'duplicate template endpoint')
    def places(name): return {p['id']:p['bytes'] for p in templates[name]['places']}
    for name in ('checked_Option_u64','loop_next'):
        items=places(name)
        for endpoint in ('Option_constructor','Option_return','Option_received'):
            require(items.get(endpoint)==16,'complete Option16 missing: '+name+' '+endpoint)
    items=places('copy_within_receiver')
    for endpoint in ('coerced_slice_source','received_receiver','Range_source','Range_received'):
        require(items.get(endpoint)==16,'fat receiver or Range collapsed: '+endpoint)
    items=places('read_forward_ld')
    for endpoint in ('Range_source','Range_received','Index_receiver_source','Index_receiver_received','Index_return_view_source','Index_return_view_received','expect_message_source','expect_message_received'):
        require(items.get(endpoint)==16,'read source/received full view missing')
    require(templates['read_forward_ld']['conservative_phase_union_bytes']==456,'read helper arithmetic changed')
    require(templates['write_sq_st']['conservative_phase_union_bytes']==424,'write helper arithmetic changed')
    require(424<=456,'write helper no longer bounded')
def returns_check(document):
    require(document['aggregate_bytes']==488 and document['complete_public_Result_bytes']==488,'complete Result488 missing')
    require(len(document['slots'])==5 and all(s['old_bytes']==232 and s['new_bytes']==488 and s['growth_bytes']==256 for s in document['slots']),'complete public slot expansion changed')
    extract=next(p for p in document['phases'] if p['id']=='external_extract')
    require(list(extract['owners'].values())==[488]*4,'external source/self/return/received missing')
def verify():
    inputs=read('inputs.json'); phases=read('phases.json'); templates=read('templates.json'); returns=read('return-moves.json')
    inputs_check(inputs); phases_check(phases); templates_check(templates); returns_check(returns)
    require(sha((ROOT/SOURCE).read_bytes())==EXPECTED,'wrong C3 source')
    pins={
     C3+'candidate-repo-seal.json':'7044a00eef658d8c729e7301c0923ed193ec405c6c6009989a964b3159bad12f',
     'verification/swift-semantic-adapter-root-review/G6-correction3-accounting-selection.json':'ea00518ce5033b4651460763f1c92533d024fee32a73b182d1684afa65ef80e1',
     'verification/swift-cache-state-g6-complete/seal.json':'c806b2967e37978403641c0172f3d70013b1e74c0d28128236f26fb618812597',
     'verification/swift-cache-state-g6-complete-independent/seal.json':'2813d055b2350902dd3b5deeab8c3a34a662d30d5ecdf25974fc13c624c44c73',
    }
    for path,expected in pins.items(): require(sha((ROOT/path).read_bytes())==expected,'selection identity drift '+path)
    inheritance=read('inheritance.json')
    for row in inheritance['source_prefix_bindings']:
        data=(ROOT/(C3+'source/library/'+row['name']+'.rs')).read_bytes()
        prefix=data[:row['inherited_prefix_bytes']]
        require(sha(prefix)==row['inherited_prefix_sha256'] and data[row['inherited_prefix_bytes']:].decode()==row['appended_utf8'],'inherited source prefix drift')
    names=read('named-places.json')['places']
    require(len({row['id'] for row in names})==len(names),'named place identity duplicate')
    require(any(row['id']=='cache_walk.arena@1090' and row['bytes']==8 and row['origin']=='new' for row in names),'thin outer arena8 missing')
    require(any(row['id']=='cache_body.arena@1322' and row['bytes']==24 and row['role']=='Setup' for row in names),'Vec24 owner missing')
    lines=(ROOT/SOURCE).read_text().splitlines()
    sites=read('source-sites.json')
    for row in sites['loops']+sites['copy_sites']+sites['checked_Option_sites']:
        require(lines[row['line']-1]==row['excerpt'],'source site excerpt drift')
    require(len([r for r in sites['copy_sites'] if 781<=r['line']<=796])==16,'clear sites missing')
    require(len([r for r in sites['copy_sites'] if 797<=r['line']<=808])==12,'restore sites missing')
    tests=[]
    def negative(label,document,checker,mutate):
        damaged=copy.deepcopy(document); mutate(damaged)
        try: checker(damaged)
        except (ValueError,KeyError,StopIteration): tests.append({'case':label,'rejected':True})
        else: raise ValueError('negative escaped: '+label)
    negative('Result232 regression',returns,returns_check,lambda d:d.update(complete_public_Result_bytes=232))
    negative('input hash drift',inputs,inputs_check,lambda d:d['members'][0].update(sha256='0'*64))
    negative('role over-cap',phases,phases_check,lambda d:d['phases'][0]['added_places'].append({'place':'bad','bytes':1281,'role':'Control','endpoint':'bad'}))
    negative('duplicate live endpoint',phases,phases_check,lambda d:d['phases'][0]['added_places'].append(d['phases'][0]['added_places'][0].copy()))
    negative('anonymous array omitted',phases,phases_check,lambda d:d['phases'].__setitem__(slice(None),[p for p in d['phases'] if p['id']!='cleanup.anonymous128.00']))
    negative('Option received omitted',templates,templates_check,lambda d:d['templates']['loop_next']['places'].__setitem__(slice(None),[p for p in d['templates']['loop_next']['places'] if p['id']!='Option_received']))
    negative('slice receiver narrowed',templates,templates_check,lambda d:next(p for p in d['templates']['copy_within_receiver']['places'] if p['id']=='received_receiver').update(bytes=8))
    negative('unassigned margin spent',phases,phases_check,lambda d:d.update(global_unassigned_margin_used=1))
    negative('acceptance overclaim',phases,phases_check,lambda d:d.update(whole_lifetime_proof_accepted=True))
    return {'status':'offline-proposal-custody-and-arithmetic-pass','python':sys.version,'named_places':len(names),'phase_templates':len(phases['phases']),'added_role_peaks':phases['added_role_peaks'],'fixed_union_bytes':29344,'negative_controls':tests,'whole_lifetime_accepted':False,'product_or_native_executed':False}
if __name__=='__main__': print(json.dumps(verify(),indent=2,sort_keys=True))
