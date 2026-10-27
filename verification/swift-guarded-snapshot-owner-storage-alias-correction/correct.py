"""Separate, fail-closed correction of frozen owner source-role inheritance.

No compiler/runtime collection, floor selection, writer dispatch, or input writes.
The source matcher works within explicit migrated function regions and requires
exact concrete type, materialized role and use shape. Source text alone is never
an inheritance authority. Ambiguous or changed operation occurrences are charged.
"""
from collections import Counter, defaultdict
from pathlib import Path
import copy, difflib, hashlib, json, re, sys
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
PRODUCER = ROOT.parent / 'swift-guarded-snapshot-owner-storage-closure'
sys.path.insert(0, str(PRODUCER))
from probe import INPUT, ENC, canonical, sha, verify
from close_recipe import closure_key, add
from layouts import instantiate

OLD_VM = ROOT.parent / 'swift-guarded-snapshot-encoder-implementation/source/vm'
NEW_VM = INPUT / 'source/vm'
PREACCESS = ROOT.parent / 'swift-guarded-snapshot-owner-storage-independent/preaccess'
PRODUCER_SEAL = 'afd33c1df35e4072e582789a38c14372f9a8efc4c6243301df4399e4899f2e4b'
PREACCESS_SEAL = 'acce273e604a3c868789af271dc4160e25a498f9dddbfaef24c2bb7d0caaa879'
TOKEN = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|[A-Za-z_][A-Za-z_0-9]*|\d+|[^\s]', re.S)
SPAN = re.compile(r' at source/([^:]+):(\d+):(\d+): (\d+):(\d+)')

def save(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def custody():
    for root, digest in [(PRODUCER, PRODUCER_SEAL), (PREACCESS, PREACCESS_SEAL)]:
        seal = (root/'seal.json').read_bytes()
        assert sha(seal) == digest
        manifest = json.loads(seal)
        for row in manifest['members']:
            data = (root/row['path']).read_bytes()
            assert len(data) == row['bytes'] and sha(data) == row['sha256'], row['path']
    baseline = json.loads((PRODUCER/'baseline-custody.json').read_text())
    for row in baseline['members']:
        data = (OLD_VM/row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256'], row['path']
    assert sha(canonical(baseline['members'])) == baseline['accepted_source_tree_sha256']
    return {'producer_seal_sha256': PRODUCER_SEAL, 'preaccess_seal_sha256': PREACCESS_SEAL,
            'baseline_source_tree_sha256': baseline['accepted_source_tree_sha256'], **verify()}

class Source:
    def __init__(self, vm, path, first, last):
        self.path = path
        self.text = (vm/'src'/path).read_text()
        self.starts = [0]
        for line in self.text.splitlines(keepends=True):
            self.starts.append(self.starts[-1] + len(line))
        self.tokens = [(m.group(), m.start(), m.end()) for m in TOKEN.finditer(
            self.text, self.starts[first-1], self.starts[last])
            if not m.group().startswith(('//', '/*'))]

    def indices(self, source):
        a = self.starts[source['start_line']-1] + source['start_column']-1
        b = self.starts[source['end_line']-1] + source['end_column']-1
        return tuple(i for i, t in enumerate(self.tokens) if a <= t[1] and t[2] <= b)

    def snippet(self, source):
        a = self.starts[source['start_line']-1] + source['start_column']-1
        b = self.starts[source['end_line']-1] + source['end_column']-1
        return self.text[a:b]

def source_region(vm, f, bounds=None):
    first, last = bounds or (min(r['source']['start_line'] for r in f['roles']),
                             max(r['source']['end_line'] for r in f['roles']))
    return Source(vm, f['source']['path'], first, last)

def concrete_type(r, vm):
    return closure_key(instantiate(r['compiler_type'], 'original'), vm)

def canonical_op(text, vm, role=None):
    # OriginalAdoptionV1::foundation is the exact unchanged legacy call. This
    # substitution is bound below to its frozen implementation, not inferred
    # from equal result sizes.
    text = instantiate(text, 'original')
    text = closure_key(text, vm)
    text = text.replace('<P as ClosedAdoptionV1>::foundation', 'foundation_construction_bytes')
    text = re.sub(r'alloc\d+', 'same-immutable-allocation', text)
    if role:
        text = re.sub(r'(?<![A-Za-z0-9_])_\d+',
                      lambda m: '$self' if m[0] == role['mir_local'] else '$other', text)
    text = re.sub(r'\bbb\d+\b', 'bb', text)
    return re.sub(r'\s+', '', text)

def use_shapes(r, vm):
    out = []
    for use in r['uses']:
        if use.startswith(('StorageLive(', 'StorageDead(', 'fn ')):
            continue
        instruction = use.split('//', 1)[0].strip().split(' -> ', 1)[0]
        out.append(canonical_op(instruction, vm, r))
    return tuple(out)

def spans_for_uses(r, predicate=lambda _: True):
    rows = []
    for use in r['uses']:
        m = SPAN.search(use)
        if m and predicate(use):
            a,b,c,d = map(int, m.group(2,3,4,5))
            rows.append({'path':m[1], 'start_line':a, 'start_column':b,
                         'end_line':c, 'end_column':d})
    return rows

def body_catalog(path):
    out = {}
    for m in re.finditer(r'(?m)^fn .*?\n\}', path.read_text(), re.S):
        body = m[0]; name = body.splitlines()[0][3:].split('(',1)[0]
        out['owner::'+name] = body
    return out

def direct_guarded_drop(body, role):
    # Compiler drop flags are identified by the actual owned place whose
    # destructor the true branch guards, never by their shared `}` span.
    drops = []
    for m in re.finditer(r'switchInt\(copy '+re.escape(role['mir_local'])+
                         r'\) -> \[0: bb\d+, otherwise: (bb\d+)\]', body):
        block = re.search(r'    '+m[1]+r'(?: \(cleanup\))?: \{(.*?)\n    \}', body, re.S)
        assert block
        drop = re.search(r'\bdrop\((.*?)\) -> ', block[1])
        if drop:
            drops.append(drop[1])
    return sorted(set(drops))

def is_drop_flag(r):
    return r['compiler_type']=='bool' and r['source_text']=='}'

def mapped_span(r, ns, os, mapping):
    indices = ns.indices(r['source'])
    return tuple(mapping.get(i, -1) for i in indices) if indices else None

def migration(f, old_by_name):
    name = f['name']
    if f['funding_class'].startswith('shared-'):
        old_name = name.replace('construct_profile_core_v1','construct_with_initial_profile_v1').replace('::adopt_body_core_v1','::adopt_body')
        return old_by_name[old_name], None, 'relocated original core or exact nested closure'
    if f['source']['path'].endswith('control.rs') and f['source']['return_line']==1837:
        old = next(g for g in old_by_name.values() if g['name'].endswith('::adopt_body'))
        return old, (698,703), 'moved Original source-then-metadata ticket refunds only'
    if f['source']['path'].endswith('retained_profile_loader_v1.rs') and f['source']['return_line'] in (165,169):
        old = next(g for g in old_by_name.values() if g['source']['path'].endswith('retained_profile_loader_v1.rs'))
        return old, None, 'same ordinary carrier ABI' if f['source']['return_line']==165 else 'moved authentic selected body destructuring and literal only'
    return None

def evidence(f, r, g, old, rule, source_rule, new_source, old_source):
    def contexts(role, source):
        return [{'source':s,'text':source.snippet(s)} for s in spans_for_uses(
            role,lambda u:not u.startswith(('StorageLive(', 'StorageDead(', 'fn ')))]
    return {'new_id':r['id'], 'old_id':old['id'], 'new_function':f['id'], 'old_function':g['id'],
            'migration':rule, 'identity_rule':source_rule,
            'new_source':r['source'], 'old_source':old['source'],
            'new_source_member_sha256':r['source_member_sha256'],
            'old_source_member_sha256':old['source_member_sha256'],
            'concrete_original_type':concrete_type(r, NEW_VM),
            'kind':r['kind'], 'debug_names':r['debug_names'],
            'new_source_text':new_source.snippet(r['source']),
            'old_source_text':old_source.snippet(old['source']),
            'new_uses':r['uses'], 'old_uses':old['uses'],
            'new_material_use_source_contexts':contexts(r,new_source),
            'old_material_use_source_contexts':contexts(old,old_source),
            'new_material_use_shapes':use_shapes(r, NEW_VM),
            'old_material_use_shapes':use_shapes(old, OLD_VM)}

def build():
    binding = custody()
    raw = json.loads((PRODUCER/'raw-inventory.json').read_text())
    original = json.loads((PRODUCER/'inventory.json').read_text())
    result = copy.deepcopy(original)
    # This defect repair may relocate a previously claimed legacy discount to
    # its proved source occurrence, but may not claim new baseline credits.
    allowed_old_ids = {(r['inherited_alias'] or {}).get('old_id') for r in original['roles']}
    allowed_old_ids.discard(None)
    old_by_name = {f['name']:f for f in raw['baseline_functions']}
    new_bodies = body_catalog(PRODUCER/'function-bodies.mir')
    old_bodies = body_catalog(PRODUCER/'inherited-function-bodies.mir')
    # A single allowed semantic call rewrite is exact in the Original impl.
    control = (NEW_VM/'src/experimental_swift_reactor/control.rs').read_text()
    assert 'fn foundation()->Option<usize>{foundation_construction_bytes()}' in control
    aliases = {}; used_old = set(); notes=[]; contexts={}
    for f in raw['functions']:
        migr = migration(f, old_by_name)
        if not migr:
            continue
        g,bounds,rule = migr
        ns,os = source_region(NEW_VM,f),source_region(OLD_VM,g,bounds)
        mapper={}
        for block in difflib.SequenceMatcher(None,[x[0] for x in ns.tokens],[x[0] for x in os.tokens],autojunk=False).get_matching_blocks():
            for i in range(block.size): mapper[block.a+i]=block.b+i
        contexts[f['id']] = {'old_function':g['id'],'migration':rule,
                              'new_token_count':len(ns.tokens),'old_token_count':len(os.tokens),
                              'aligned_token_count':len(mapper),'old_region_bounds':bounds}
        for r in f['roles']:
            if is_drop_flag(r):
                continue
            candidates=[]; source_rule=''
            for old in g['roles']:
                if old['id'] in used_old or is_drop_flag(old): continue
                if (r['kind'],r['debug_names'],concrete_type(r,NEW_VM)) != (old['kind'],old['debug_names'],concrete_type(old,OLD_VM)): continue
                if r['kind'] in ('parameter','return-expression'):
                    # Only preserved core ABI or the one ordinary carrier ABI.
                    if bounds or f['source']['return_line']==169: continue
                    if r['kind']=='parameter' and r['mir_local']!=old['mir_local']: continue
                    candidates.append(old);source_rule='same Original-specialized migrated function ABI position and binding; actual uses retained'
                    continue
                mapped=mapped_span(r,ns,os,mapper)
                exact=mapped is not None and -1 not in mapped and mapped==os.indices(old['source'])
                # This named successful foundation payload is the same Original
                # source occurrence after its explicitly bound closed dispatch.
                foundation = (r['source_text'].startswith('P::foundation().ok_or_else') and
                              old['source_text'].startswith('foundation_construction_bytes().ok_or_else') and
                              r['mir_local']==old['mir_local'] and use_shapes(r,NEW_VM)==use_shapes(old,OLD_VM))
                if not (exact or foundation): continue
                if r['kind']=='temporary' and use_shapes(r,NEW_VM)!=use_shapes(old,OLD_VM):
                    # Moving a refund to its trait helper changes only the
                    # receiver's borrow path: local control -> *control argument.
                    # Both source refund occurrences and their ordered ticket
                    # patterns remain exact within the separately bounded region.
                    moved_receiver = (bounds==(698,703) and
                        concrete_type(r,NEW_VM)=='&mut experimental_swift_reactor::control::RuntimeControl' and
                        tuple(x.replace('&mut(*$other)','&mut$other') for x in use_shapes(r,NEW_VM))==use_shapes(old,OLD_VM))
                    if not moved_receiver:continue
                    source_rule='exact ordered moved refund receiver occurrence and call; local-to-parameter reborrow path explicit'
                candidates.append(old)
                if not (r['kind']=='temporary' and bounds==(698,703) and
                        use_shapes(r,NEW_VM)!=use_shapes(old,OLD_VM)):
                    source_rule='exact token occurrence in explicit migrated function/region plus material use shape' if exact else 'exact closed Original foundation substitution, occurrence and material use shape'
            if len(candidates)==1:
                old=candidates[0]
                row=evidence(f,r,g,old,rule,source_rule,ns,os)
                if old['id'] not in allowed_old_ids:
                    notes.append({'new_id':r['id'],'status':'unselected optional baseline credit',
                                  'evidence':row})
                    continue
                used_old.add(old['id']);aliases[r['id']]=row
            elif len(candidates)>1:
                notes.append({'new_id':r['id'],'status':'charged: ambiguous source occurrence',
                              'candidates':[q['id'] for q in candidates]})
        # All non-flag identities are now fixed. Guarded destructor operands can
        # consequently be compared through the already established owner map.
        def drop_key(role, body, current):
            drops=direct_guarded_drop(body,role)
            if drops:
                def replace(m):
                    rid=f['id']+'::'+m[0] if current else g['id']+'::'+m[0]
                    return aliases.get(rid,{}).get('old_id','unproved-current:'+rid) if current else rid
                return ('guarded-owned-place',tuple(re.sub(r'(?<![A-Za-z0-9_])_\d+',replace,x) for x in drops))
            # Dead compiler flags have no destructor branch. Exact true-source
            # occurrence + material use shape and ordinal distinguish them.
            true_spans=spans_for_uses(role,lambda u:'= const true;' in u)
            if not true_spans:return None
            span=true_spans[0]
            idx=ns.indices(span) if current else os.indices(span)
            if current:idx=tuple(mapper.get(i,-1) for i in idx)
            if not idx or -1 in idx:return None
            return ('no-destructor-branch',idx,use_shapes(role,NEW_VM if current else OLD_VM))
        old_flags=defaultdict(list)
        for old in g['roles']:
            if is_drop_flag(old) and old['id'] not in used_old:
                k=drop_key(old,old_bodies[g['id']],False)
                if k:old_flags[k].append(old)
        for r in f['roles']:
            if not is_drop_flag(r):continue
            k=drop_key(r,new_bodies[f['id']],True)
            candidates=old_flags.get(k,[]) if k else []
            if candidates:
                old=candidates.pop(0);used_old.add(old['id'])
                row=evidence(f,r,g,old,rule,'actual guarded owned place, or exact dead-flag true occurrence/use shape and ordered occurrence',ns,os)
                row['drop_identity_key']=k;row['new_guarded_drops']=direct_guarded_drop(new_bodies[f['id']],r)
                row['old_guarded_drops']=direct_guarded_drop(old_bodies[g['id']],old)
                aliases[r['id']]=row
    # Recompute every role's actual charge; never preserve an unproved discount.
    by_function={f['id']:f for f in raw['functions']}
    for r in result['roles']:
        f=by_function[r['template']];alias=aliases.get(r['id'])
        r['inherited_alias']=None if alias is None else {
            'old_id':alias['old_id'],'old_source':alias['old_source'],
            'old_source_member_sha256':alias['old_source_member_sha256'],
            'alias_rule':alias['identity_rule'],'evidence_packet':'inherited-aliases.json'}
        charges={k:0 for k in original['formulas']};cls=f['funding_class']
        if cls.startswith('shared-'):
            ob=max(v['bytes'] for v in r['actual_variants'] if v['profile']=='original')
            sb=max(v['bytes'] for v in r['actual_variants'] if v['profile']=='selected')
            if alias is None:charges['common-extra']=ob
            charges['selected-unconditional']=max(0,sb-ob)
        elif cls=='common':
            if alias is None:charges['common-extra']=r['bytes']
        else:charges[cls]=r['bytes']
        r['funding']=charges
    sums={k:0 for k in result['formulas']}
    for r in result['roles']:
        for k,n in r['funding'].items():sums[k]=add(sums[k],n)
    result['owner_only_formulas']=dict(sums)
    sums['selected-unconditional']=add(sums['selected-unconditional'],result['encoder_join']['unconditional_bytes'])
    sums['admitted-only']=add(sums['admitted-only'],result['encoder_join']['admitted_only_bytes'])
    result['formulas']=sums
    for f in result['functions']:
        f['additional_bytes']=sum(sum(r['funding'].values()) for r in result['roles'] if r['template']==f['id'])
    assert len(aliases)==len(used_old)
    return result, aliases, notes, contexts, binding

def write():
    d,aliases,notes,contexts,binding=build()
    old=json.loads((PRODUCER/'inventory.json').read_text())
    prior={r['id']:r for r in old['roles']}
    changed=[]
    for r in d['roles']:
        q=prior[r['id']]
        if r['inherited_alias']!=q['inherited_alias'] or r['funding']!=q['funding']:
            old_id=(q['inherited_alias'] or {}).get('old_id');new_id=(r['inherited_alias'] or {}).get('old_id')
            if old_id!=new_id or r['funding']!=q['funding']:
                changed.append({'id':r['id'],'kind':r['kind'],'compiler_type':r['compiler_type'],
                                'source':r['source'],'source_text':r['source_text'],
                                'before_old_id':old_id,'after_old_id':new_id,
                                'before_funding':q['funding'],'after_funding':r['funding'],
                                'status':'inherited occurrence reassigned' if new_id else 'unproved inherited identity charged as new'})
    all_old=[r for f in json.loads((PRODUCER/'raw-inventory.json').read_text())['baseline_functions'] for r in f['roles']]
    optional=[q for q in notes if q['status']=='unselected optional baseline credit']
    save('optional-credits-unselected.json',{'schema':1,'selected':False,'correspondences':optional,
         'rule':'Previously unused legacy slots are outside this defect repair. Existing conservative charge is retained; no floor reduction is selected.'})
    save('inherited-aliases.json',{'schema':1,'aliases':list(aliases.values()),
         'alias_count':len(aliases),'baseline_role_count':len(all_old),
         'retained_unused_legacy_ids':[r['id'] for r in all_old if r['id'] not in {a['old_id'] for a in aliases.values()}],
         'rule':'function/explicit moved-region + exact source occurrence + concrete Original type + material use/controlled-drop evidence; no family text pooling',
         'source_binding':binding,'function_migrations':contexts,
         'ambiguities_charged':[q for q in notes if q['status']!='unselected optional baseline credit'],
         'new_legacy_credits_selected':False})
    save('funding.json',{'schema':1,'source_binding':binding,'roles':[
         {'id':r['id'],'funding':r['funding'],'inherited_old_id':(r['inherited_alias'] or {}).get('old_id')} for r in d['roles']],
         'role_count':len(d['roles']),'function_count':len(d['functions']),
         'owner_only_formulas':d['owner_only_formulas'],'formulas':d['formulas'],
         'host_caller_bytes':d['host_caller_bytes'],'encoder_join':d['encoder_join']})
    formula=json.loads((PRODUCER/'formula.json').read_text())
    formula.update(common_extra=d['formulas']['common-extra'],selected_unconditional_extra=d['formulas']['selected-unconditional'],
                   admitted_only_extra=d['formulas']['admitted-only'],owner_only=d['owner_only_formulas'],
                   inherited_alias_count=len(aliases),producer_seal_sha256=PRODUCER_SEAL,
                   independent_final_review_pending=True)
    save('formula.json',formula)
    save('delta.json',{'schema':1,'before':old['formulas'],'after':d['formulas'],
         'delta':{k:d['formulas'][k]-old['formulas'][k] for k in d['formulas']},
         'before_alias_count':357,'after_alias_count':len(aliases),'changed_roles':changed,
         'source_layout_changes':False,'runtime_executions':0,'const_floor_selection':False})
    print(json.dumps({'aliases':len(aliases),'changed_roles':len(changed),'formulas':d['formulas'],
                      'delta':{k:d['formulas'][k]-old['formulas'][k] for k in d['formulas']}}))

if __name__=='__main__':
    write()
