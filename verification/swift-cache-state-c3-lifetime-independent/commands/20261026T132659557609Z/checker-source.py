#!/usr/bin/env python3
"""Independent offline custody, bounded schedule and mutation review.

The reviewed source is data. No Rust or producer Python is imported/executed.
Source coordinates support the independently authored review, not OTA authority.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROPOSAL = ROOT / 'verification/swift-cache-state-c3-lifetime-accounting'
C3 = ROOT / 'verification/swift-cache-state-implementation/correction-3'
SOURCE = C3 / 'source/library/cache_state.rs'
SOURCE_SHA = '0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8'
PROPOSAL_SHA = '703bf7ca338dac74574c60a7ac42addcd4d1bc44645d559dd05ca0c4dad56c22'
CANDIDATE_SHA = '7044a00eef658d8c729e7301c0923ed193ec405c6c6009989a964b3159bad12f'
BASE = {'Control':6656,'Wire':2616,'Setup':5168,'Report':4296,'IO':1472,'Metadata':2400,'Candidate':2048}
ADDED_CAP = {'Control':1280,'Wire':256,'Setup':256,'Report':2896,'IO':0,'Metadata':0,'Candidate':0}
RESERVED = {'Control':8192,'Wire':3072,'Setup':12288,'Report':8192,'IO':4096,'Metadata':4096,'Candidate':2048}
CHECKS = 0


def demand(condition, message):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def bind(path, expected, size=None):
    data = path.read_bytes()
    demand(sha(data) == expected, 'identity drift: ' + str(path))
    if size is not None:
        demand(len(data) == size, 'size drift: ' + str(path))
    return data


def frozen_inputs():
    seal = json.loads(bind(PROPOSAL/'seal.json', PROPOSAL_SHA))
    demand(seal['member_count'] == 36 and seal['member_bytes'] == 483656,
           'wrong frozen producer packet')
    demand(len(seal['members']) == 36, 'manifest count')
    demand(sum(r['bytes'] for r in seal['members']) == 483656, 'manifest bytes')
    for row in seal['members']:
        path = ROOT / row['path']
        demand(path.is_relative_to(PROPOSAL), 'producer member escaped packet')
        bind(path, row['sha256'], row['bytes'])
    inputs = read(PROPOSAL/'inputs.json')['members']
    for row in inputs:
        bind(ROOT/row['path'], row['sha256'], row['bytes'])
    candidate = json.loads(bind(C3/'candidate-repo-seal.json', CANDIDATE_SHA))
    rows = candidate['source_rows']
    demand(rows == sorted(rows, key=lambda r:r['path']), 'source rows not sorted')
    tree = sha(json.dumps(rows, sort_keys=True, separators=(',',':')).encode())
    demand(tree == '45bd39ce40ce25cba9304dfd014d8ad3da1b9ee83f9e55de91618da8b77d7dac',
           'candidate source-row digest')
    demand(tree == candidate['source_tree_digest'], 'candidate declared tree digest')
    libraries = [r for r in rows if r['path'].startswith('source/library/')]
    demand(len(libraries) == 3, 'library closure changed')
    for row in libraries:
        bind(C3/row['path'], row['sha256'], row['bytes'])
    inheritance = read(PROPOSAL/'inheritance.json')
    for row in inheritance['source_prefix_bindings']:
        whole = (C3/('source/library/'+row['name']+'.rs')).read_bytes()
        old = (ROOT/('verification/swift-envelope-absent-state-correction/proposal-1/src/'+row['name']+'.rs')).read_bytes()
        demand(whole[:len(old)] == old, 'actual predecessor prefix mismatch')
        demand(len(old) == row['inherited_prefix_bytes'], 'prefix size')
        demand(sha(old) == row['inherited_prefix_sha256'], 'prefix SHA')
        demand(whole[len(old):].decode() == row['appended_utf8'], 'unreviewed suffix')
    acceptance = read(ROOT/inheritance['root_acceptance'])
    demand(acceptance['implementation_accepted'] is True, 'predecessor not selected')
    demand(acceptance['accounting']['logical_bytes'] == 24656, 'predecessor role sum')
    inventory = read(ROOT/inheritance['selected_inventory'])
    demand(sum(inventory['named_role_upper_by_group'].values()) == 24656,
           'predecessor inventory arithmetic')
    demand({k.capitalize():v for k,v in inventory['named_role_upper_by_group'].items()} == BASE,
           'predecessor complete role identities')
    g6 = read(ROOT/'verification/swift-semantic-adapter-root-review/G6-correction3-accounting-selection.json')
    demand(g6['production']['groups'] == 512 and g6['including_private_faults']['groups'] == 514,
           'wrong selected G6')
    demand(g6['whole_role_union_accepted'] is False, 'G6 became lifetime authority')
    return {'producer_members':36,'producer_member_bytes':483656,'referenced_inputs':len(inputs),
            'candidate_source_tree_digest':tree,'library_files_directly_hashed':3,
            'candidate_full570_member_replay':False,'predecessor_closure_replayed':False}


def source_navigation(text):
    lines = text.splitlines()
    demand(lines[709].strip() == 'let stage = match w[1] {', 'stage birth changed')
    demand(lines[767].strip() == 'SemanticReply {', 'final reply start changed')
    demand(lines[772].strip() == '}', 'semantic lexical end changed')
    demand(lines[1087].strip() == 'z' and lines[1088].strip() == '}', 'projection return changed')
    for line, expected in [(967,'let child ='),(1018,'let Some(f) = f else {'),
                           (1032,'let q = &p.q;'),(1033,'let stage = q[3];'),
                           (1034,'let active = stage != 0;'),
                           (1035,'let planned = (6..=10).contains(&stage);'),
                           (1036,'let pending = stage == 7 || stage == 8;')]:
        demand(lines[line-1].strip() == expected, 'projection named owner drift')
    for i in range(16):
        expected = f'c[{i*128}..{(i+1)*128}].copy_from_slice(&[0u8; 128]);'
        demand(lines[780+i].strip() == expected, 'anonymous clear must stay statement-scoped')
    restore_starts = [888,896,904,912,920,928,936,944,952,960,968,976]
    restore_sources = [7729816,7729832,7729840,7729848,7729856,7729864,7729872,7730272,7730280,7730288,7731040,7731048]
    for line, dst, src in zip(range(797,809), restore_starts, restore_sources):
        demand(lines[line-1].strip() == f'c[{dst}..{dst+8}].copy_from_slice(&b[{src}..{src+8}]);',
               'restore must alias existing payload')
    demand(text.count('c.copy_within(1944..2008, 1536);') == 2, 'receiver sites changed')
    demand('let received = semantic(' in text and 'if !cleanup(&arena.bytes, &mut candidate)' in text,
           'actual semantic/cleanup caller changed')
    demand('for i in 0..16 {\n                            p.q[i] = cq(&candidate, i);' in text,
           'actual post-reply snapshot changed')
    return lines


def producer_arithmetic(phases, names, templates, returns):
    demand(len(names) == 191 and len({r['id'] for r in names}) == 191, 'named identities')
    by_id = {r['id']:r for r in names}
    for name, size, end in [('semantic.stage@710',8,773),('projection.child@967',8,1089),
                           ('projection.f_binding@1018',8,1089),('projection.q@1032',8,1089),
                           ('projection.stage@1033',8,1089),('projection.active@1034',1,1089),
                           ('projection.planned@1035',1,1089),('projection.pending@1036',1,1089),
                           ('cache_walk.arena@1090',8,1268),('cache_body.arena@1322',24,1395),
                           ('cache_walk.loan@1183',16,1230),('cache_walk.semantic_steps@1187',16,1230),
                           ('cache_walk.received_semantic@1193',24,1230)]:
        demand(by_id[name]['bytes'] == size and by_id[name]['lexical_end_line'] == end,
               'critical named owner narrowed: '+name)
    demand(len(phases['phases']) == 39, 'phase count')
    for row in phases['phases']:
        labels = [r['place'] for r in row['added_places']]
        demand(len(labels) == len(set(labels)), 'duplicate live owner')
        for role in BASE:
            subtotal = sum(p['bytes'] for p in row['added_places'] if p['role'] == role)
            demand(subtotal == row['added_totals'][role], 'producer subtotal')
            demand(row['inherited_upper'][role] == BASE[role], 'inherited credit')
            demand(row['composed_upper'][role] == BASE[role]+subtotal, 'composition arithmetic')
            demand(subtotal <= ADDED_CAP[role], 'producer added allowance')
    for key, want in [('read_forward_ld',456),('write_sq_st',424),('checked_Option_u64',160),
                      ('copy_within_receiver',145),('copy_from_two_ranges',256),('loop_next',80),('loop_setup',64)]:
        row = templates[key]
        demand(sum(p['bytes'] for p in row['places']) == want, 'complete endpoint arithmetic')
    for key in ['loop_next','checked_Option_u64']:
        d = {p['id']:p['bytes'] for p in templates[key]['places']}
        for field in ['Option_constructor','Option_return','Option_received']:
            demand(d[field] == 16, 'complete Option16 required including None')
    d = {p['id']:p['bytes'] for p in templates['copy_within_receiver']['places']}
    for field in ['coerced_slice_source','received_receiver','Range_source','Range_received']:
        demand(d[field] == 16, 'complete fat receiver/Range required')
    demand(returns['aggregate_bytes'] == returns['complete_public_Result_bytes'] == 488,
           'complete public Result488 including Err required')
    demand(len(returns['slots']) == 5, 'five predecessor aggregate slots')
    demand(all(r['old_bytes'] == 232 and r['new_bytes'] == 488 and r['growth_bytes'] == 256
               for r in returns['slots']), 'full five-slot expansion')
    demand(5*(488-232)+5*256+4*32 == 2688 <= ADDED_CAP['Report'], 'report independent derivation')
    extract = next(p for p in returns['phases'] if p['id'] == 'external_extract')
    demand(sorted(extract['owners'].values()) == [488]*4, 'source/self/designated/received extraction')
    demand(4*488 <= 5*488, 'extraction fits five whole capacities')
    demand(104+128+256 == 488, 'whole aggregate fields')
    demand(phases['whole_lifetime_proof_accepted'] is False, 'producer acceptance overclaim')


def addendum_check(addendum, findings):
    demand(addendum['source_sha256'] == SOURCE_SHA, 'addendum source identity')
    expected_bases = {'walk':248,'semantic_pre_probe':392,'semantic_probe':480,
                      'semantic_after_body':488,'walk_after_semantic':304}
    for key, want in expected_bases.items():
        demand(sum(addendum['bases'][key].values()) == want, 'source owner base '+key)
    schedules = {r['id']:r for r in addendum['schedules']}
    demand(len(schedules) == 18, 'finite supplement lost a schedule')
    for row in schedules.values():
        demand(sum(row['Control_groups'].values()) == row['Control'], 'independent Control arithmetic')
        demand(0 <= row['Control'] <= 1280, 'independent Control overflow')
        for role in ['Setup','Wire','Report']:
            demand(row[role] <= ADDED_CAP[role], 'independent '+role+' overflow')
        demand(all(1 <= lo <= hi <= 1419 for lo,hi in row['source_spans']), 'unbound source region')
    reply = schedules['semantic-final-reply-corrected']
    demand(reply['Control_groups'].get('stage_omitted_by_producer') == 8 and reply['Control'] == 584,
           'L1 named stage disappeared')
    project = schedules['projection-final-return-corrected']
    demand(project['Control_groups'].get('child_f_q_stage') == 32 and
           project['Control_groups'].get('active_planned_pending') == 3 and project['Control'] == 275,
           'L2 named projection locals disappeared')
    demand(schedules['actual-caller-snapshot-after-reply']['Control_groups']['walk_after_semantic'] == 304,
           'post-reply caller owners disappeared')
    demand(schedules['all-loop-setup-next-final-None']['Control_groups']['complete_next_including_iterator'] == 80,
           'final None complete endpoints lost')
    maxima = {'Control':1201,'Wire':152,'Setup':160,'Report':2688}
    for role, value in maxima.items():
        demand(max(r[role] for r in schedules.values()) <= value, 'new peak exceeds frozen allowance')
        demand(addendum['retained_'+role+'_peak'] == value, 'frozen peak changed')
    demand(findings['findings'][0]['bytes'] == 8 and findings['findings'][1]['bytes'] == 35,
           'finite omissions changed')
    demand(findings['root_selection_required'] is True and findings['whole_lifetime_acceptance_granted'] is False,
           'independent review cannot self-select root acceptance')
    demand(sum(BASE.values()) == 24656 and sum(ADDED_CAP.values()) == 4688, 'role partition')
    demand(sum(BASE[k]+ADDED_CAP[k] for k in BASE) == 29344, 'fixed union')
    demand(sum(RESERVED.values()) == 41984 and 65536-41984 == 23552, 'reservation/margin')
    for role in BASE:
        demand(BASE[role]+ADDED_CAP[role] <= RESERVED[role], 'reservation role fit')


def run():
    custody = frozen_inputs()
    source = bind(SOURCE,SOURCE_SHA,47006).decode()
    source_navigation(source)
    phase_doc = read(PROPOSAL/'phases.json')
    names = read(PROPOSAL/'named-places.json')['places']
    templates = read(PROPOSAL/'templates.json')['templates']
    returns = read(PROPOSAL/'return-moves.json')
    addendum = read(HERE/'coverage-addendum.json')
    findings = read(HERE/'findings.json')
    producer_arithmetic(phase_doc,names,templates,returns)
    addendum_check(addendum,findings)
    mutations = []

    def reject(label, value, mutate, check):
        changed = copy.deepcopy(value)
        mutate(changed)
        try:
            check(changed)
        except (ValueError,KeyError,StopIteration):
            mutations.append({'case':label,'rejected':True})
        else:
            raise ValueError('independent mutation escaped: '+label)

    def schedule(doc, name):
        return next(r for r in doc['schedules'] if r['id'] == name)

    reject('retire stage at last use',addendum,
           lambda d:schedule(d,'semantic-final-reply-corrected')['Control_groups'].pop('stage_omitted_by_producer'),
           lambda d:addendum_check(d,findings))
    reject('retire projection flags before return',addendum,
           lambda d:schedule(d,'projection-final-return-corrected')['Control_groups'].pop('active_planned_pending'),
           lambda d:addendum_check(d,findings))
    reject('omit actual post-reply snapshot',addendum,
           lambda d:d['schedules'].remove(schedule(d,'actual-caller-snapshot-after-reply')),
           lambda d:addendum_check(d,findings))
    reject('borrow global margin for Control overflow',addendum,
           lambda d:schedule(d,'prefix-checked-helper').update(Control=1281),
           lambda d:addendum_check(d,findings))
    reject('narrow complete Option final None',templates,
           lambda d:next(p for p in d['loop_next']['places'] if p['id']=='Option_received').update(bytes=8),
           lambda d:producer_arithmetic(phase_doc,names,d,returns))
    reject('collapse received fat receiver',templates,
           lambda d:next(p for p in d['copy_within_receiver']['places'] if p['id']=='received_receiver').update(bytes=8),
           lambda d:producer_arithmetic(phase_doc,names,d,returns))
    reject('remove outer arena pointer8',names,
           lambda d:d.remove(next(r for r in d if r['id']=='cache_walk.arena@1090')),
           lambda d:producer_arithmetic(phase_doc,d,templates,returns))
    reject('regress complete public Result232',returns,
           lambda d:d.update(complete_public_Result_bytes=232),
           lambda d:producer_arithmetic(phase_doc,names,templates,d))
    reject('drop one inherited232-to488 slot',returns,
           lambda d:d['slots'].pop(),lambda d:producer_arithmetic(phase_doc,names,templates,d))
    reject('count only active Err32',returns,
           lambda d:d.update(aggregate_bytes=32),lambda d:producer_arithmetic(phase_doc,names,templates,d))
    reject('duplicate contained field payload',phase_doc,
           lambda d:d['phases'][0]['added_places'].append({'place':'duplicated-contained-cache-state','role':'Report','bytes':256}),
           lambda d:producer_arithmetic(d,names,templates,returns))
    reject('grant lifetime acceptance without root selection',findings,
           lambda d:d.update(whole_lifetime_acceptance_granted=True),
           lambda d:addendum_check(addendum,d))
    try:
        source_navigation(source.replace('c[0..128].copy_from_slice(&[0u8; 128]);',
                                         'let named = [0u8; 128]; c[0..128].copy_from_slice(&named);',1))
    except ValueError:
        mutations.append({'case':'replace anonymous clear with named source/local','rejected':True})
    else:
        raise ValueError('named clear mutation escaped')
    demand(128+128+24 == 280 > 256, 'named-array initializer/local overflows Wire allowance')
    demand(128+24 == 152 <= 256, 'selected anonymous clear Wire arithmetic')
    demand(sha(source.replace('let stage = match w[1]', 'let stage = match w[2]',1).encode()) != SOURCE_SHA,
           'source drift must fail identity')
    mutations.append({'case':'source digest drift','rejected':True})
    return {'status':'independent-finite-review-with-bounded-corrections',
            'python':sys.version,'optimized':bool(sys.flags.optimize),'checks':CHECKS,
            'source_sha256':SOURCE_SHA,'producer_seal_sha256':PROPOSAL_SHA,
            'custody':custody,'producer_named_places':191,'producer_phases':39,
            'independent_supplement_schedules':18,
            'confirmed_omissions':{'semantic_final_reply_stage':8,'projection_final_return_locals':35},
            'corrected_rows':{'semantic_final_reply_Control':584,'projection_final_return_Control':275},
            'added_role_peaks':{'Control':1201,'Wire':152,'Setup':160,'Report':2688},
            'fixed_union':29344,'reserved':41984,'ceiling':65536,'margin_used':0,
            'mutation_cases':mutations,'root_selection_required':True,
            'original_exact_phase_completeness_accepted':False,
            'whole_lifetime_acceptance_granted':False,'implementation_accepted':False,
            'compiler_product_native_UI_capture_process_inventory_Git_or_hosted_actions':False,
            'product_or_old_packets_mutated':False,'GA_qualified':False}


if __name__ == '__main__':
    print(json.dumps(run(),indent=2,sort_keys=True))
