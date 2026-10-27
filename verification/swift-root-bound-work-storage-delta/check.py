#!/usr/bin/env python3
"""Bounded offline source/MIR delta reconstruction. Never calls subprocess/network.

Use --build once to create the review inventory; default checks its exact finite
mapping against retained source/MIR. This proves inventory integrity/coverage,
not Rust semantics, layouts, prices, allocation backing, or release admission.
"""
import argparse
import copy
import difflib
import gzip
import hashlib
import json
import platform
import resource
import sys
import time
from collections import Counter
from pathlib import Path

import contract as C

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
resource.setrlimit(resource.RLIMIT_CPU, (25, 25))
MAX_INPUT = 210_000_000
MAX_FILE = 4_500_000
MAX_MIR = 90_000_000
READ = 0
PINS = {}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(rel, limit=MAX_FILE):
    global READ
    path = ROOT / rel
    size = path.stat().st_size
    assert size <= limit, ('file-byte-bound', rel, size)
    READ += size
    assert READ <= MAX_INPUT, ('total-byte-bound', READ)
    data = path.read_bytes()
    PINS[rel] = {'bytes': len(data), 'sha256': sha(data)}
    return data


def jsread(rel):
    return json.loads(read(rel))


def expect(a, b, label):
    if a != b:
        raise AssertionError(label)


def function_match(header, selector):
    # Finite selectors only, not a general Rust or MIR parser.
    return header.startswith('fn ' + selector + '(') or ('::' + selector + '(' in header) or (selector.startswith('drop(') and ('>::' + selector in header))


def select(items, selector):
    matches = [x for x in items if x.get('kind', 'fn') == 'fn' and function_match(x['header'], selector)]
    if selector == 'usage_v1':
        matches = [x for x in matches if 'RootBoundFixtureOutcomeV1' in x['header']]
    assert len(matches) == 1, ('nonunique-finite-selector', selector, len(matches))
    return matches[0]


def source_span(lane, rel, a, b, cache):
    key = (lane, rel)
    if key not in cache:
        cache[key] = read(lane + '/source/vm/' + rel)
    lines = cache[key].splitlines(keepends=True)
    data = b''.join(lines[a-1:b])
    return {'path': lane + '/source/vm/' + rel, 'first_line': a, 'last_line': b, 'sha256': sha(data), 'bytes': len(data)}


def stream_mir(lane, inventory, selected, baseline=False):
    global READ
    if baseline:
        full = inventory['full_MIR']
        archive = full['archive']
        uncompressed = {'bytes': full['uncompressed_bytes'], 'sha256': full['uncompressed_sha256']}
    else:
        archive, uncompressed = inventory['archive'], inventory['complete_mir']
    compressed = read(lane + '/' + archive['path'])
    expect({'bytes': len(compressed), 'sha256': sha(compressed)}, {k: archive[k] for k in ['bytes', 'sha256']}, 'archive-pin')
    # Stream every gzip byte once for custody, retain selected spans only.
    # Baseline inventory supplies line intervals; current one supplies byte spans.
    retained = {key: bytearray() for key in selected}
    total, digest, line_no, byte_no = 0, hashlib.sha256(), 0, 0
    import io
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
        for line in stream:
            line_no += 1
            digest.update(line)
            total += len(line)
            assert total <= MAX_MIR, 'decompression-byte-bound'
            if baseline:
                for key, item in selected.items():
                    if item['first_line'] <= line_no <= item['last_line']:
                        retained[key].extend(line)
            else:
                # Item boundaries are line aligned in this pinned inventory.
                for key, item in selected.items():
                    if item['byte_start'] <= byte_no < item['byte_end_exclusive']:
                        retained[key].extend(line)
            byte_no += len(line)
    READ += total
    assert READ <= MAX_INPUT, 'total-decompressed-byte-bound'
    expect(total, uncompressed['bytes'], 'full-mir-byte-count')
    expect(digest.hexdigest(), uncompressed['sha256'], 'full-mir-sha256')
    out = {}
    for key, item in selected.items():
        data = bytes(retained[key])
        # Baseline functions omit the following blank line. Current complete item
        # spans include it. Verify each inventory's own documented exact boundary.
        expect(len(data), item['bytes'], 'selected-mir-byte-count:' + key)
        expect(sha(data), item['sha256'], 'selected-mir-sha256:' + key)
        out[key] = data
    return out, {'archive_path': lane + '/' + archive['path'], 'archive': archive,
                 'uncompressed': uncompressed, 'read_mode': 'single gzip stream; selected spans only retained in memory',
                 'selected_retained_bytes': sum(map(len, out.values()))}


def classify(line):
    s = line.strip().split('//', 1)[0].strip()
    if not s or s in ['{', '}'] or s.startswith('scope '):
        return None
    if s.startswith('fn '): return 'argument_signature'
    if s.startswith('let '): return 'return_place' if '_0:' in s else 'local_place'
    if s.startswith('debug '): return 'capture_field' if '(_1.' in s else 'source_local_binding'
    if s.startswith('bb'): return 'cleanup_block' if '(cleanup)' in s else 'block'
    # Every remaining compiler line is represented. Tags are descriptive and
    # overlapping; this is deliberately not an instruction-price decoder.
    tags = []
    if s.startswith('StorageLive('): tags.append('storage_live')
    if s.startswith('StorageDead('): tags.append('storage_dead')
    if 'drop(' in s or 'std::mem::drop::' in s: tags.append('drop')
    if 'unwind' in s or s.startswith(('resume;', 'terminate(')): tags.append('unwind')
    if '-> [return:' in s: tags.append('call_or_drop')
    if 'copy ' in s: tags.append('copy')
    if 'move ' in s: tags.append('move')
    if s.startswith('return;'): tags.append('return')
    if ' = &' in s: tags.append('borrow')
    if 'discriminant(' in s or s.startswith('switchInt('): tags.append('branch')
    return '+'.join(tags) or 'other_explicit_statement'


def mir_rows(data, first_line, obligations):
    rows = []
    for offset, raw in enumerate(data.splitlines(keepends=True)):
        kind = classify(raw.decode())
        if kind:
            row = {'line': first_line+offset, 'kind': kind,
                   'sha256': sha(raw), 'obligations': obligations}
            if kind in ['local_place','return_place']:
                declaration = raw.decode().strip().split('//',1)[0].strip()
                place, ty = declaration.removeprefix('let ').removeprefix('mut ').split(': ',1)
                row['place'] = place
                row['storage_role'] = storage_role(ty.rstrip(';'),obligations)
            rows.append(row)
    return rows


def storage_role(ty, obligations):
    """Explicit representation/backing distinction; no inferred byte layout."""
    if ty.startswith('&'):
        kind = 'root_reference_representation' if 'BootstrapLedgerV1' in ty else 'borrowed_reference_representation'
        backing = 'pointee remains separately owned/charged; reference representation is not payload backing'
    elif ty.startswith('{closure@'):
        kind,backing = 'actual_anonymous_closure_representation','capture-owned fields and borrowed pointees must be reviewed separately; no captured-field proxy layout'
    elif any(t in ty for t in ['RootBound','AdmittedFixture','OwnedCorrelationOutcome','CorrelatedSelectedProfile']):
        kind,backing = 'bound_envelope_or_envelope_aggregate','complete carried payload backing retained through final destruction; root reference does not fund it'
    elif any(t in ty for t in ['File','SelectedValidatedProfile','Loader','RawFixture','RawCorrelation','Cancellation','SnapshotScope','SnapshotPreScope',' T','<T>','PrepaidOwned','SetupOutcome']):
        kind,backing = 'payload_or_payload_aggregate','inline representation plus separately retained owned/shared backing; moves do not imply new allocation'
    else:
        kind,backing = 'other_representation_or_control','all representation storage remains unresolved; no payload backing inferred from type spelling'
    return {'type_spelling':ty,'representation_class':kind,'backing_distinction':backing,
            'obligations':[x for x in obligations if x.startswith('S')],
            'layout':'UNOBSERVED_FOR_THIS_TREE','no_numeric_floor_from_MIR_slots':True}


def argument_places(header,obligations):
    args = header.split('(',1)[1].rsplit(') -> ',1)[0]
    fields,depth,start=[],0,0
    for index,char in enumerate(args):
        if char in '<({[': depth+=1
        elif char in '>)}]': depth-=1
        elif char==',' and depth==0:
            fields.append(args[start:index].strip());start=index+1
    if args[start:].strip(): fields.append(args[start:].strip())
    out=[]
    for field in fields:
        place,ty=field.split(': ',1)
        assert place.startswith('_'),('argument-place-parser',header,field)
        out.append({'place':place,'storage_role':storage_role(ty,obligations),
                    'evidence':'exact pinned MIR header; not a source-based ABI layout observation'})
    return out


def derive():
    cs = read(C.CAND + '/seal.json')
    expect(sha(cs), C.CAND_SEAL, 'released-candidate-seal')
    seals = {C.CAND: json.loads(cs), C.BASE: jsread(C.BASE + '/seal.json')}
    origin = jsread(C.CAND + '/source-origin.json')
    expect(PINS[C.BASE + '/seal.json']['sha256'],origin['base_seal']['sha256'],'baseline-seal-from-frozen-candidate-origin')
    cm = jsread(C.CAND + '/source-manifest.json')
    bm = jsread(C.BASE + '/source-manifest.json')
    expect(cm['tree_sha256'], C.CAND_TREE, 'candidate-source-tree')
    expect(bm['tree_sha256'], C.BASE_TREE, 'baseline-source-tree')
    expect(cm['member_count'], 146, 'candidate-source-count')
    expect(bm['member_count'], 146, 'baseline-source-count')
    old, new = ({m['path']:m for m in d['members']} for d in [bm, cm])
    expect(set(old), set(new), 'source-member-closure')
    changed = sorted(k for k in old if old[k] != new[k])
    expect(changed, sorted([C.LOADER,C.CACHE]), 'exact-two-source-delta')
    expect(cm['changed'], changed, 'declared-two-source-delta')
    cache = {}
    for lane, manifest in [(C.CAND,new),(C.BASE,old)]:
        for rel in [C.LOADER,C.CACHE,C.CHILD]:
            data = read(lane + '/source/vm/' + rel)
            expect({'bytes':len(data),'sha256':sha(data)}, {k:manifest[rel][k] for k in ['bytes','sha256']}, 'changed-or-child-source-custody')
            cache[(lane,rel)] = data
    review = jsread(C.REVIEW)
    expect(review['candidate_source_tree_sha256'], C.CAND_TREE, 'independent-review-source')
    expect(review['new_places_requiring_later_MIR_layout_funding_review'], [r[0] for r in C.REVIEW_CLASSES], 'independent-nine-obligation-classes')
    transition = jsread(C.CAND + '/private-transition-inventory.json')
    expect(transition['source146_tree'], C.CAND_TREE, 'transition-source')
    transition_map = []
    for site in transition['finite_production_transitions']:
        names = site['site'].split('::')[-1].split('/')
        matches = [f for f in C.FUNCTIONS if f[0] in names]
        expect(len(matches),len(names),'finite-private-transition-coverage:'+site['site'])
        transition_map.append({'site':site['site'],'functions':[f[0] for f in matches],
                               'obligations':sorted({o for f in matches for o in f[-1]})})
    ci = jsread(C.CAND + '/complete-mir-item-inventory.json')
    bi = jsread(C.BASE + '/mir-function-inventory.json')
    baseline_complete = jsread(C.BASE + '/complete-mir-item-inventory.json')
    producer = jsread(C.CAND + '/mir-function-inventory.json')
    jsread(C.CAND + '/toolchain.json')
    jsread(C.CAND + '/commands-v2/production-MIR/plan.json')
    read(C.BASE + '/contract.md')
    selected, previous = {}, {}
    for selector, rel, a, b, old_selector, status, obligations in C.FUNCTIONS:
        selected[selector] = select(ci['items'], selector)
        if old_selector:
            previous[selector] = select(bi['functions'], old_selector)
    # Producer roster includes 24 constructor/shim entries, all retained by
    # individual exact index. Two emitted occurrences are not two runtime calls.
    constructors = []
    for item in producer['items_containing_new_types']:
        it = item['item']
        if it['index'] not in {x['index'] for x in selected.values()}:
            expect(ci['items'][it['index']],it,'producer-MIR-roster-custody')
            assert it['index'] >= 4097, ('unmapped-body',it['header'])
            key = 'constructor:' + str(it['index'])
            selected[key] = it
            constructors.append(key)
    expect(len(constructors),24,'constructor-occurrences')
    expect(len(selected),48,'finite-selected-function-count')
    mir, current_archive = stream_mir(C.CAND, ci, selected)
    oldmir, baseline_archive = stream_mir(C.BASE, bi, previous, True)
    # The baseline complete inventory must contain each selected old function;
    # its complete-item blank-line boundary can differ from the function roster.
    for key,it in previous.items():
        assert any(x['header']==it['header'] for x in baseline_complete['items']), ('baseline-complete-item-missing',key)
    types = []
    for name, rel, a,b,status,fields,obligations in C.TYPES:
        span = source_span(C.CAND,rel,a,b,cache)
        assert name.encode() in b''.join(cache[(C.CAND,rel)].splitlines(keepends=True)[a-1:b]), ('type-anchor',name)
        types.append({'name':name,'source':span,'delta':status,'fields_or_variants':fields,'obligations':obligations})
    functions = []
    for selector,rel,a,b,old_selector,status,obligations in C.FUNCTIONS:
        it = selected[selector]
        span = source_span(C.CAND,rel,a,b,cache)
        anchor = b'|| run_prepaid_admitted_fixture_v1' if '::{closure#0}' in selector else selector.split('(')[0].encode()
        assert anchor in b''.join(cache[(C.CAND,rel)].splitlines(keepends=True)[a-1:b]), ('function-anchor',selector)
        entry = {'selector':selector,'delta':status,'source':span,'MIR':it,'obligations':obligations,
                 'argument_places':argument_places(it['header'],obligations),
                 'rows':mir_rows(mir[selector],it['line_start'],obligations)}
        if old_selector:
            entry['baseline_MIR'] = previous[selector]
            entry['baseline_rows'] = mir_rows(oldmir[selector],previous[selector]['first_line'],obligations)
        functions.append(entry)
    for key in constructors:
        it = selected[key]
        name = it['header'].split('fn ',1)[1].split('(',1)[0].split('::',1)[0]
        matching = [t for t in types if t['name']==name]
        assert len(matching)==1, ('constructor-type-map',name)
        t = matching[0]
        functions.append({'selector':key,'delta':'COMPILER_CONSTRUCTOR_OR_SHIM_OCCURRENCE','source':t['source'],
                          'MIR':it,'obligations':t['obligations'],
                          'argument_places':argument_places(it['header'],t['obligations']),
                          'rows':mir_rows(mir[key],it['line_start'],t['obligations'])})
    # Three exact fields, mapped from actual closure MIR, not inferred by summing
    # named captured-field layouts.
    closure = mir['run_one_admitted_fixture_v1::{closure#0}'].decode().splitlines()
    captures = [s for s in closure if s.lstrip().startswith('debug ')]
    expect(len(captures),3,'actual-closure-field-count')
    for s,name,field in zip(captures,['fixture','attempt','expected'],['(_1.0:','(_1.1:','(_1.2:']):
        assert ('debug '+name+' =>') in s and field in s, ('actual-closure-capture',name)
    # All changed source line intervals are retained, including explicit test,
    # probe-only and reexport exclusions. No assertion that source diff == work.
    source_deltas = []
    for rel in changed:
        a = cache[(C.BASE,rel)].decode().splitlines(keepends=True)
        b = cache[(C.CAND,rel)].decode().splitlines(keepends=True)
        chunks=[]
        for tag,oa,ob,na,nb in difflib.SequenceMatcher(a=a,b=b,autojunk=False).get_opcodes():
            if tag!='equal':
                chunks.append({'operation':tag,'baseline_lines_half_open':[oa+1,ob+1],
                               'candidate_lines_half_open':[na+1,nb+1],
                               'baseline_sha256':sha(''.join(a[oa:ob]).encode()),
                               'candidate_sha256':sha(''.join(b[na:nb]).encode())})
        source_deltas.append({'path':rel,'chunks':chunks})
    obligations = [{'id':k,'delta':v[0],'name':v[1],'required_positive_obligation':v[2],
                    'price':'UNRESOLVED','layout_or_backing_bound':'UNRESOLVED'} for k,v in C.OBLIGATIONS.items()]
    allrefs = set(x for f in functions for x in f['obligations']) | set(x for t in types for x in t['obligations'])
    expect(allrefs,set(C.OBLIGATIONS),'orphan-or-unknown-obligation')
    # Only claim custody of files actually read; all candidate/baseline inputs
    # must be members of their already-frozen packet, not merely self-hashed.
    for lane,seal in seals.items():
        members={x['path']:x for x in seal['members']}
        for path,pin in PINS.items():
            if path.startswith(lane+'/') and path!=lane+'/seal.json':
                rel=path[len(lane)+1:]
                assert rel in members,('frozen-input-not-a-member',path)
                expect(pin,{k:members[rel][k] for k in ['bytes','sha256']},'frozen-input-member-pin:'+path)
    data = {'schema':1,'status':'offline-delta-preparation-awaiting-independent-review-and-layout-pricing',
            'baseline_source146_tree':C.BASE_TREE,'candidate_source146_tree':C.CAND_TREE,
            'claim_limits':C.LIMITS,'inputs':PINS,'source_deltas':source_deltas,
            'source146_members_checked':'both pinned manifests compared; only two changed files and unchanged generic child source read; no full146 copy or hash replay',
            'obligations':obligations,'types':types,'functions_and_constructor_occurrences':functions,
            'independent_new_place_classes':[{'class':s,'obligations':o} for s,o in C.REVIEW_CLASSES],
            'producer_private_transition_coverage':transition_map,
            'actual_dispatch_captures':{'MIR_item_index':1237,'fields':['fixture by value','attempt by value (contains original root reference)','expected shared reference'],
                                      'obligations':['W07','S01','S05','S06'],'anonymous_layout_observed':False},
            'MIR_custody':{'candidate':current_archive,'baseline':baseline_archive},
            'relocation':{'old':'run_prepaid_admitted_fixture_v1 matched branch + invoke_loaded_leaf_once_v1/run_one_loaded_fixture_v1',
                          'new':'OwnedCorrelationOutcomeV1::run_fixture_once_v1 fixed synchronous frame',
                          'work_obligation':'W04','storage_obligations':['S04','S08','S09','S11'],
                          'no_duplicate_leaf_invocation_inferred':True},
            'destruction_and_lifetime_intervals':[
              {'places':'correspondence/attempt root fields; scope root local/tuple/return','begin':'copied from exact self.owned.reservation.root when scope issued','end':'association input destruction or last accessible view; selected output separately owns same root reference','required':['S01','S02','S10']},
              {'places':'generic core/facade return and selected envelopes','begin':'whole original carrier received before any correlation check','end':'complete payload moves to next bound envelope or complete destruction, including error/refusal and unwind','required':['W02','W03','W09','S02','S03','S08','S11']},
              {'places':'fixed fixture raw payload/arguments/branch tuple/scope/run/finish','begin':'whole bound outcome plus all FixtureLeafArguments consumed','end':'both typed original leaf arms and all files/usage/rows/snapshot/cancellation/claims re-enclosed, or cleanup on unwind','required':['W04','W05','W09','S04','S08','S09','S10','S11']},
              {'places':'admitted setup/loaded root field and child wrapper','begin':'attempt.original_root_v1 before setup_files_once_v1','end':'complete setup refusal or loaded child payload destruction; ordinary Drop never releases charge','required':['W07','W08','W09','W10','S05','S08','S09','S10','S11']},
              {'places':'primary/inspect shared views and scalar copies','begin':'short shared borrow of live complete child/fixture','end':'borrow ends before whole child destruction; output scalar has no original payload','required':['W06','S07']},
              {'places':'child destruction/transient payload Option and returned child token','begin':'complete PrepaidOwned<child,AdmittedFixtureOutcome<root>> consumed','end':'payload dropped before child reservation taken; token is child-only after destroy returns; panic returns no token','required':['W09','W10','S05','S11','S12']},
              {'places':'root acquisition charge','begin':'pre-existing IR01 acquisition reservation, sticky scope barrier set before publication','end':'no useful post-scope joint release selected; mem::forget may end accessible handle lifetime without proving durable root funding','required':['S10']}],
            'drop_evidence_limit':'new types have implicit field/variant drops. Selected generic MIR includes drop terminators/cleanup, not every monomorphized standard-library or drop-glue body. W09/S11 remain positive unresolved dependencies; counts are not destructor prices.',
            'explicit_scope_exclusions':[
              'Test-only Guard/Trace/panic injection and changed test callsites are not production work or layout observations.',
              'cfg-only compile-probe include sites add no ordinary production API; test-positive helper excluded.',
              'split_pair_v1 is a production-source generic body with test-only callsites, explicitly inventoried.',
              'scoped_binding_v1 and outer identity/preimage map closure have unchanged bodies; enclosing impl lifetime changes are representation rebind prerequisites S01/W11, not invented new operations.',
              'OriginalCorrelationRefusalV1 fields and supplied carrier retain helper are unchanged; complete original payload backing still required.',
              'Existing untouched unadmitted entry and raw helper remain outside admitted-family guarantee.',
              'No complete source/MIR duplicate retained here; row hashes point to authoritative retained archives.'],
            'counts':{'types':len(types),'handwritten_or_dependency_functions':len(C.FUNCTIONS),'constructor_or_shim_occurrences':len(constructors),
                      'candidate_MIR_rows':sum(len(f['rows']) for f in functions),
                      'candidate_argument_places':sum(len(f['argument_places']) for f in functions),
                      'candidate_local_and_return_places':sum(sum(r['kind'] in ['local_place','return_place'] for r in f['rows']) for f in functions),
                      'baseline_MIR_rows':sum(len(f.get('baseline_rows',[])) for f in functions),
                      'obligations':len(obligations),'independent_new_place_classes':len(C.REVIEW_CLASSES)}}
    return data


def validate(expected, observed):
    expect(observed,expected,'finite-source-MIR-mapping-or-claim-mismatch')


def negative_controls(expected):
    # Each control removes or falsifies a material receipt obligation; all are
    # in-memory copies, never mutations of frozen source or prior lanes.
    mutations = [
      ('missing-root-field',lambda d:d['types'][0]['fields_or_variants'].pop()),
      ('missing-type',lambda d:d['types'].pop()),
      ('missing-function',lambda d:d['functions_and_constructor_occurrences'].pop(0)),
      ('missing-local-place',lambda d:next(f for f in d['functions_and_constructor_occurrences'] if f['selector']=='correlate_core_v1')['rows'].pop(1)),
      ('missing-unwind-row',lambda d:next(f for f in d['functions_and_constructor_occurrences'] if f['selector']=='run_fixture_once_v1')['rows'].__setitem__(slice(None),[r for r in next(f for f in d['functions_and_constructor_occurrences'] if f['selector']=='run_fixture_once_v1')['rows'] if 'unwind' not in r['kind']])),
      ('wrong-source-span',lambda d:d['types'][0]['source'].__setitem__('first_line',1964)),
      ('wrong-MIR-span',lambda d:d['functions_and_constructor_occurrences'][0]['MIR'].__setitem__('byte_start',0)),
      ('wrong-baseline-tree',lambda d:d.__setitem__('baseline_source146_tree',C.CAND_TREE)),
      ('lost-review-class',lambda d:d['independent_new_place_classes'].pop()),
      ('closure-pointee-ownership',lambda d:d['actual_dispatch_captures']['fields'].__setitem__(2,'expected payload owned by value')),
      ('invented-price',lambda d:d['obligations'][0].__setitem__('price',0)),
      ('invented-layout',lambda d:d['obligations'][12].__setitem__('layout_or_backing_bound',8)),
      ('implied-funding',lambda d:d['claim_limits'].__setitem__('total_funding_accepted',True)),
      ('changed-input-hash',lambda d:next(iter(d['inputs'].values())).__setitem__('sha256','0'*64)),
      ('double-leaf-charge',lambda d:d['relocation'].__setitem__('no_duplicate_leaf_invocation_inferred',False)),
    ]
    result=[]
    for name,mutation in mutations:
        bad=copy.deepcopy(expected)
        mutation(bad)
        assert bad!=expected, ('ineffective-negative',name)
        try: validate(expected,bad)
        except AssertionError: result.append({'name':name,'intended_rejection':True})
        else: raise AssertionError(('accepted-adverse-control',name))
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--build',action='store_true')
    args=parser.parse_args()
    started=time.monotonic()
    expected=derive()
    path=HERE/'delta-inventory.json'
    if args.build:
        path.write_text(json.dumps(expected,indent=2)+'\n')
    observed=json.loads(path.read_text())
    validate(expected,observed)
    negatives=negative_controls(expected)
    summary={'status':'PASS_FINITE_OFFLINE_MAPPING_ONLY','python':sys.version,
             'command':['python3','-B',str(Path(__file__).resolve())]+(['--build'] if args.build else []),
             'platform':platform.platform(),'elapsed_seconds':round(time.monotonic()-started,6),
             'source_revision_kind':'exact frozen source146 tree digests; current checkout HEAD not product authority',
             'baseline_source_tree':C.BASE_TREE,'candidate_source_tree':C.CAND_TREE,
             'counts':expected['counts'],'input_bytes_including_full_gzip_streams':READ,
             'bound':{'input_bytes':MAX_INPUT,'individual_input_bytes':MAX_FILE,'each_uncompressed_MIR_bytes':MAX_MIR,'CPU_seconds':25},
             'negative_controls':negatives,'claim_limits':C.LIMITS,
             'cleanup':{'compiler_or_native_children_started':0,'network_requests':0,'process_inventories':0,
                        'source_or_MIR_copies_created':0,'temporary_files':0,'python_bytecode_disabled':sys.dont_write_bytecode,
                        'only_lane_local_JSON_written':bool(args.build)}}
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
