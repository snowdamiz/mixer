#!/usr/bin/env python3
"""Independent offline, necessary-subtrace review. Never imports producer code."""
import collections
import copy
import gzip
import hashlib
import json
import pathlib
import random
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
OLD = ROOT / 'verification/swift-cache-state-seeded-first-pass-proposal'
FULL = ROOT / 'verification/swift-cache-state-row-probe-proposal/source/cache_state.rs.txt'
SOURCE = 'a43397ec7cbbec398502acae5911394fced7ed8d220fee096589940eafb49fb1'
U64 = (1 << 64) - 1
BINDINGS = {
 'verification/swift-cache-state-row-probe-proposal/seal.json': '8d3317005e5db2b6114a9bd2be3c40682920f20041a5b46bd22d50ae929aab7f',
 'verification/swift-cache-state-row-probe-independent/seal.json': '4918dfa723161e9cead7087e066baf8021efe64a9a27dee67a6e8518f61c365e',
 'verification/swift-semantic-adapter-root-review/row-probe-G2-selection.json': '80d78642b67d9e8164532868e56bfc2bdbeb3fcd3b2756bd9b4580c06e0123bf',
 'verification/swift-semantic-adapter-root-review/G6-correction3-accounting-selection.json': 'ea00518ce5033b4651460763f1c92533d024fee32a73b182d1684afa65ef80e1',
 'verification/swift-cache-state-seeded-first-pass-proposal/seal.json': 'b27e1ee4d0a55d35ac6fff5c1d7d7256019e4caea3b17dce000a77021b0475f1',
 'verification/swift-cache-state-row-probe-independent/source-audit.json': '5e5a78b286f332e054764d794fdb0e20d1dc77cf6ac83257e360e48165a74921',
 'verification/swift-cache-state-row-probe-independent/check.py': '1da35f6ec43d895a57c5b029d95f30894fc2005934c23535c4e51121d839bd5a',
 'verification/swift-cache-state-row-probe-independent/ownership-boundaries.json': '40d4297e22f9ec7e4163030be5c3490f24f144a4398ce7009c809283adc465e5',
 'verification/swift-cache-state-row-probe-proposal/components.json': 'b0001d7fdb0397b35a115ba80ff63d65875c2f9a786d07bf0f42f21b2864c24c',
 'verification/swift-cache-state-g6-complete-independent/review-findings.json': '95ba8d4103df869fc3ec692432f3df61d42483acb25390470f4db458a9123feb',
 'verification/swift-cache-state-g6-complete-independent/audit.py': 'b6feb52560f8e957978261f3921ca7d527995943d0c247f6eebb4bc473f3bcee',
}

def need(ok, msg):
    if not ok:
        raise ValueError(msg)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def read(p):
    return json.loads(p.read_bytes())

def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')

def cost(events):
    s = sum(e['kind'] == 'scalar' for e in events)
    c = sum(e['kind'] == 'copy' for e in events)
    return dict(scalars=s, copies=c, scalar_groups=(s + 15) // 16,
                groups=(s + 15) // 16 + c)

def custody():
    for n, h in BINDINGS.items():
        need(sha((ROOT / n).read_bytes()) == h, 'binding digest ' + n)
    need(sha(FULL.read_bytes()) == SOURCE, 'source digest')
    used = ['source/merge.rs.txt', 'component-templates.json',
            'finite-subtrace-ledger.json.gz', 'merge-witness.json', 'subtrace-summary.json']
    seal = read(OLD / 'seal.json')
    members = {x['path']: x for x in seal['members']}
    result = dict(BINDINGS)
    result[str(FULL.relative_to(ROOT))] = SOURCE
    for n in used:
        p = OLD / n
        rel = str(p.relative_to(ROOT))
        m = members[rel]
        need(p.stat().st_size == m['bytes'] and sha(p.read_bytes()) == m['sha256'], 'seeded member digest')
        result[rel] = m['sha256']
    return result

def source_map(source):
    need(sha(source.encode()) == SOURCE, 'source digest')
    merge = (OLD / 'source/merge.rs.txt').read_text()
    need(source.count(merge) == 1, 'merge bytes changed')
    lines = source.splitlines()
    initial = []
    head = ['{', 'let index = s.indices[s.lp];', 's.li = index as u16;',
            'if index != u8::MAX {', 's.lt = u64::from_le_bytes(s.timestamps[index as usize]);', '}',
            'let index = s.indices[s.rp];', 's.ri = index as u16;',
            'if index != u8::MAX {', 's.rt = u64::from_le_bytes(s.timestamps[index as usize]);', '}', '}']
    for i, line in enumerate(lines):
        if line.strip() == head[1] and lines[i-1].strip() == '{':
            need([z.strip() for z in lines[i-1:i+11]] == head, 'initial block source shape')
            initial.append(dict(start=i, end=i+11, left=i+1, right=i+6))
    need(len(initial) == 31, 'initial head block domain')
    outputs = {}
    for i, line in enumerate(lines):
        m = re.search(r'// p([1-5])\.out([0-9]+): fully expanded emit expression\.', line)
        if m:
            key = (int(m[1]), int(m[2]))
            need(key not in outputs, 'output source duplicate')
            outputs[key] = i+1
    need(set(outputs) == {(p, i) for p in range(1,6) for i in range(64)}, 'output source domain')
    reloads = {}
    for (p,out), line in outputs.items():
        # Boundary resets/initial heads precede the choice. The first left and
        # right loads after that choice are the two authored emit branches.
        choice = next(i for i in range(line,len(lines)) if lines[i].strip() == 'let take_left = if s.ri >= 255 {')
        for side,field in [('l','lp'),('r','rp')]:
            at = next(i for i in range(choice,len(lines)) if lines[i].strip()==f'let index = s.indices[s.{field}];')
            value, timestamp = ('li','lt') if side=='l' else ('ri','rt')
            need([z.strip() for z in lines[at:at+5]] == [
                 f'let index = s.indices[s.{field}];',f's.{value} = index as u16;',
                 'if index != u8::MAX {',
                 f's.{timestamp} = u64::from_le_bytes(s.timestamps[index as usize]);','}'], 'reload source shape')
            reloads[f'{p}:{out}:{side}']=at+1
    seeds = {}
    seed_choices=[]
    for i,line in enumerate(lines):
        m=re.search(r'let (left|right) = if eligibility & (0x[0-9a-f]{16})u64 != 0 \{ ([0-9]+)u8 \} else \{ u8::MAX \};',line)
        if m:
            slot=int(m[3]);need(int(m[2],16)==1<<slot,'seed mask literal')
            need(m[1]==('left' if slot%2==0 else 'right'),'seed side')
            need(str(slot) not in seeds,'seed source duplicate')
            seeds[str(slot)]=i+1
        if line.strip()=='let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };':
            seed_choices.append(i+1)
    need(set(seeds)=={str(i) for i in range(64)} and len(seed_choices)==32,'seed source domain')
    need(source.count('merge(c);') == 1, 'merge caller domain')
    need('let eligibility = ld(c, 640);' in source, 'eligibility load source')
    ld = source[source.index('fn ld('):source.index('\nfn st(')]
    need(ld == '''fn ld(b: &[u8], at: usize) -> u64 {
    u64::from_le_bytes(
        *b[at..at + 8]
            .first_chunk::<8>()
            .expect("proved eight-byte range"),
    )
}''', 'ld helper source')
    # Selected G2 itself contains the lexical pair, independently supplemented
    # by completed-if pairs. Its final if is the block's final source expression.
    comp = read(ROOT / 'verification/swift-cache-state-row-probe-proposal/components.json')
    post = comp['templates']['post.success']
    need([e['operation'] for e in post[-2:]] ==
         ['G2 lexical block implicit unit', 'G2 lexical block exit continuation'], 'selected lexical pair')
    selected = (ROOT / 'verification/swift-cache-state-row-probe-independent/check.py').read_text()
    need("scalars(condition,['if.unit','if.continuation'])" in selected, 'selected if pair')
    need("'tail.assignment.unit_and_continuation':2" in selected, 'selected assignment pair')
    return dict(initial=initial, outputs={f'{p}:{i}': n for (p,i),n in outputs.items()},
                reloads=reloads,seeds=seeds,seed_choices=seed_choices,
                merge_start=source[:source.index(merge)].count('\n')+1,
                merge_sha256=sha(merge.encode()), merge_bytes=len(merge.encode()),
                eligibility_line=next(i+1 for i,l in enumerate(lines) if l.strip() == 'let eligibility = ld(c, 640);'),
                ld_line=next(i+1 for i,l in enumerate(lines) if l.startswith('fn ld(')))

def source_admitted_witness():
    # Exact values reaching the authored semantic merge call, assuming the
    # immutable Loan/Profile/arena admission contract. No public file is claimed.
    ts = [int(f'{i:06b}'[::-1], 2) for i in range(64)]
    residents = [[1, i, 1, 0, ts[i], 0, 0, 0] for i in range(64)]
    pins = [[U64, 0, 0, 0, 0, 0]]
    need(all(r[0] == 1 and r[3] == 0 and r[6] == 0 and r[7] == 0 for r in residents), 'resident header')
    need(all(r[1] < 80000 and 0 < r[2] <= 1 for r in residents), 'resident body')
    need(sum(r[2] for r in residents) == 64 and len(residents) == 64, 'resident totals')
    need(pins[0][0] == U64 and pins[0][1] == 0, 'empty pin')
    mask = sum(1 << i for i,r in enumerate(residents) if r[0] == 1 and r[3] == 0)
    need(mask == U64, 'eligibility')
    return dict(schema=1, source_scope='source-admitted semantic inputs; immutable Loan/Profile admission assumed',
                public_file_reachability_proved=False, timestamps=ts, eligibility_mask=mask,
                fixture=dict(slots=64,pins=1,entry=1,base=0,capacity=64), residents=residents,pins=pins,
                prior=dict(count=64,total=64,pins=0,next_nonce=1,terminal=0,stage=5),
                record=dict(kind=5,function=64,request_bytes=1,base=0,capacity=64,words7_8_9=[0,0,0]),
                function64_marker_u32=1, plan64=[64,0,0,0,0],
                premerge_guard_checks=['body64<80000 and function marker1',
                  'plan cell64 values match record words6..9; prior plan request0',
                  'request1>0 and <=entry1; base0/capacity64 match',
                  'checked base0+request1 exists and <=capacity64'],
                unproved=['admissible public framing file','real binding','all progress/public replay invariants',
                          'G5/G6 full execution','whole lifetime union','compiler/runtime/native','GA'])

def simulate(ts, mask):
    # Each source-written output block is visited exactly once. The source cursor
    # eagerly loads both heads, then reloads the emitted side unless exhausted.
    order = []
    specs = []
    passes = []
    loads = []
    blocks = []
    for pair in range(32):
        l, r = pair*2, pair*2+1
        for slot in (l,r):
            specs.append((f'width1.pair{pair}.head{slot}', 'seeded_head0', slot))
        li = l if mask & (1 << l) else 255
        ri = r if mask & (1 << r) else 255
        take_left = ri == 255 or (li != 255 and ts[l] <= ts[r])
        specs.append((f'width1.pair{pair}.choice', 'seeded_choice', None))
        order.extend([li,ri] if take_left else [ri,li])
    passes.append(dict(width=1, comparisons=32, outputs=64,timestamp_loads=64))
    for p in range(1,6):
        width = 1 << p
        new = []
        comparisons = count_load = exhaustion = 0
        for base in range(0,64,2*width):
            lp, le, rp, re_ = base, base+width, base+width, base+2*width
            li = ri = 256
            lt = rt = 0
            def load(side, out, initial):
                nonlocal li,ri,lt,rt,count_load
                pos = lp if side == 'l' else rp
                idx = order[pos]
                if side == 'l':
                    li = idx
                    if idx != 255: lt = ts[idx]
                else:
                    ri = idx
                    if idx != 255: rt = ts[idx]
                if idx != 255:
                    count_load += 1
                    specs.append((f'p{p}.out{out}.load-{side}', 'old_eligible_head', side))
                    loads.append(dict(pass_=p,out=out,side=side,initial=initial,base=base,slot=idx))
            load('l',base,True)
            load('r',base,True)
            blocks.append(dict(pass_=p,base=base))
            for out in range(base,base+2*width):
                if ri >= 255:
                    take_left = li != 256
                    template = 'old_tail_choice'
                else:
                    take_left = li < 255 and lt <= rt
                    template = 'old_pair_choice' if li < 255 else 'old_left_exhausted_choice'
                if li != 256 and ri != 256: comparisons += 1
                specs.append((f'p{p}.out{out}.choice', template, None))
                if take_left:
                    new.append(li)
                    lp += 1
                    if lp < le:
                        load('l',out,False)
                    else:
                        li = 256
                        exhaustion += 1
                        specs.append((f'p{p}.out{out}.exhausted', 'sentinel', 'l'))
                else:
                    new.append(ri)
                    rp += 1
                    if rp < re_:
                        load('r',out,False)
                    else:
                        ri = 256
                        exhaustion += 1
                        specs.append((f'p{p}.out{out}.exhausted', 'sentinel', 'r'))
        order = new
        passes.append(dict(width=width,comparisons=comparisons, outputs=64,
                           timestamp_loads=count_load,exhaustions=exhaustion))
    return dict(output=order,specs=specs,passes=passes,loads=loads,blocks=blocks)

def audit_old(sim,mapping):
    data = json.loads(gzip.decompress((OLD / 'finite-subtrace-ledger.json.gz').read_bytes()))
    templates = read(OLD / 'component-templates.json')['templates']
    # Independent hand decomposition of the selected source/operand model:
    # fixed-array Index20 includes receiver, entry, bounds, scaling, reference,
    # caller, return, and final dereference/use. Input index expression is extra.
    expected = {'seeded_head0':(10+1+20+5,1), 'seeded_choice':(6+5+7,0),
                'old_eligible_head':(2+3+20+2+3+6+2+3+20+4+3,1),
                'old_pair_choice':(8+7+8+3,0),
                'old_left_exhausted_choice':(8+7+1+3,0),
                'old_tail_choice':(8+6+3,0)}
    need(expected['old_eligible_head'] == (68,1), 'independent head equation')
    for name, (s,c) in expected.items():
        need(cost(templates[name])['scalars'] == s and cost(templates[name])['copies'] == c, 'template equation '+name)
        need(not any('continuation' in x['operation'] or 'unit' in x['operation'] for x in templates[name]), 'old template already has endpoints')
    head = templates['old_eligible_head']
    need(head[29]['operation'] == 'u16 result source -> s.li' and
         head[-1]['operation'] == 'from_le_bytes returned word -> s.lt', 'assignment terminals')
    need(sum(e['kind']=='copy' and e['bytes']==8 for e in head)==1, 'head complete array copy')
    # Retain immutable actual event labels only after matching every segment to
    # the independently executed witness and the selected primitive equations.
    segments = [s for s in data['segments'] if s['owner']=='G3']
    need(len(segments) == len(sim['specs']), 'source witness segment domain')
    audited = []
    for n, (seg, spec) in enumerate(zip(segments,sim['specs'])):
        site, name, arg = spec
        need(seg['site'] == site, 'source witness segment order')
        events = data['events'][seg['first']:seg['first']+seg['count']]
        if name == 'sentinel':
            wanted = [('scalar',0)]*3
        else:
            wanted = [(e['kind'],e['bytes']) for e in templates[name]]
        need([(e['kind'],e['bytes']) for e in events] == wanted, 'source witness event shape')
        need(all(e['owner']=='G3' and e['site']==site for e in events), 'old owner/site')
        labels = None
        if name == 'old_eligible_head':
            labels = [e['operation'] for e in head]
            if arg == 'r':
                labels = [z.replace('s.lp','s.rp').replace('s.li','s.ri').replace('s.lt','s.rt') for z in labels]
        elif name == 'seeded_head0':
            labels = [e['operation'] for e in templates[name]]
            labels[1]=f'literal 0x{1<<arg:016x}u64 source -> & right'
            labels[9]=f'literal {arg}u8 source -> left/right binding'
            labels[10]=f'literal {arg}usize source -> Index received index'
        elif name=='sentinel':
            field='li' if arg=='l' else 'ri'
            labels=[f's.{field} parent pointer -> destination projection operand',
                    f's.{field} destination field address projection',f'literal 256 source -> s.{field}']
        else:
            labels=[e['operation'] for e in templates[name]]
        need([e['operation'] for e in events] == labels,'operation correspondence')
        if site.startswith('width1.'):
            line=mapping['seeds'][str(arg)] if name=='seeded_head0' else mapping['seed_choices'][int(site.split('.')[1][4:])]
        else:
            p=int(site[1]);out=int(site.split('.')[1][3:])
            line=mapping['outputs'][f'{p}:{out}']
        for ordinal, e in enumerate(events):
            audited.append(dict(e,id=f'G3/base/{n:04d}/{ordinal:02d}',old_event_id=e['id'],
                                source_line=line,phase='baseline'))
    need(cost(audited) == dict(scalars=32929,copies=384,scalar_groups=2059,groups=2443), 'recomputed baseline')
    old_g4 = [e for e in data['events'] if e['owner']=='G4']
    need(cost(old_g4)==dict(scalars=8493,copies=12,scalar_groups=531,groups=543), 'G4 prior subtrace')
    need(not ({e['old_event_id'] for e in audited} & {e['id'] for e in old_g4}), 'baseline G3/G4 overlap')
    return audited, dict(independent_component_equations=expected, G4_unchanged_necessary_subtrace=cost(old_g4),
                         original_segment_count=len(segments),original_G3_event_count=len(audited),
                         no_producer_code_imported_or_executed=True)

def augment(base, sim, mapping):
    events = copy.deepcopy(base)
    additions = []
    def scalar(site,label,line,phase):
        additions.append(dict(id=f'G3/{site}/{label}',owner='G3',kind='scalar',bytes=0,
                              site=site,operation=label,source_line=line,phase=phase))
    for n, load in enumerate(sim['loads']):
        p, out, side = load['pass_'],load['out'],load['side']
        if load['initial']:
            block_number=next(i for i,b in enumerate(sim['blocks']) if b['pass_']==p and b['base']==load['base'])
            line=mapping['initial'][block_number]['left' if side=='l' else 'right']
        else:
            line=mapping['reloads'][f'{p}:{out}:{side}']
        stem = f'head/{n:03d}/p{p}/out{out}/{side}/'+('initial' if load['initial'] else 'reload')
        # Each assignment is a semicolon statement. The completed conditional's
        # unit and continuation are separate from both assignment statements.
        for label in ['index-assignment.unit','index-assignment.continuation',
                      'timestamp-assignment.unit','timestamp-assignment.continuation',
                      'timestamp-if.unit','timestamp-if.continuation']:
            offset=1 if label.startswith('index-assignment') else 3 if label.startswith('timestamp-assignment') else 4
            scalar(stem,label,line+offset,'later-head-endpoints')
    need(len(additions)==1920, 'later head endpoints')
    for n, block in enumerate(sim['blocks']):
        source_block = mapping['initial'][n]
        for label in ['block.implicit-unit','block.exit-continuation']:
            scalar(f'initial-block/{n:02d}/p{block["pass_"]}/base{block["base"]}',label,
                   source_block['end'],'initial-head-block-endpoints')
    # Deliberately sparse, decisive ld lower subtrace. All omitted ld range,
    # fixed-view/Option/expect/LE-return operations remain positive uncounted
    # work. This never presents18 as the complete ld cost.
    ldlabels = [
       'Candidate.array-address-formation', 'Candidate.receiver-reborrow',
       'Candidate.address->coerced-slice.data-source','Candidate.length2048->coerced-slice.len-source',
       'coerced-slice.data->ld.received.data','coerced-slice.len->ld.received.len',
       'literal640->ld.received.at','ld.entry-control',
       'ld.at->Range.start-source','ld.at->plus.left','literal8->plus.right',
       'plus.primitive','plus.result->Range.end-source','Range.start->Index.received.start',
       'Range.end->Index.received.end','ld.slice.Index-receiver-reborrow',
       'ld.slice.data->Index.received.receiver.data','ld.slice.len->Index.received.receiver.len']
    for label in ldlabels:
        scalar('eligibility-ld',label,mapping['eligibility_line'],'sparse-eligibility-ld')
    additions.append(dict(id='G3/eligibility-ld/complete-array8-source->from_le_bytes-received8',
        owner='G3',kind='copy',bytes=8,site='eligibility-ld',
        operation='complete dereferenced range array8 source -> from_le_bytes received array8',
        source_line=mapping['ld_line']+2,phase='sparse-eligibility-ld'))
    events.extend(additions)
    return events,additions

def validate(events, required_ids):
    need(len(events)==len({e['id'] for e in events}), 'duplicate event id')
    need(set(required_ids) <= {e['id'] for e in events}, 'required event omitted')
    for e in events:
        need(e['owner']=='G3', 'owner changed')
        need((e['kind']=='scalar' and e['bytes']==0) or
             (e['kind']=='copy' and 0 < e['bytes'] <=128),'primitive width')
    need(cost(events)==dict(scalars=34929,copies=385,scalar_groups=2184,groups=2569),'necessary totals')

def groups(events):
    scalars = [e['id'] for e in events if e['kind']=='scalar']
    out = [dict(kind='scalar',owner='G3',events=scalars[i:i+16]) for i in range(0,len(scalars),16)]
    out.extend(dict(kind='copy',owner='G3',bytes=e['bytes'],events=[e['id']]) for e in events if e['kind']=='copy')
    flat = [x for g in out for x in g['events']]
    need(len(flat)==len(events) and set(flat)=={e['id'] for e in events}, 'exact once groups')
    return out

def main():
    bindings = custody()
    source = FULL.read_text()
    mapping = source_map(source)
    witness = source_admitted_witness()
    sim = simulate(witness['timestamps'],witness['eligibility_mask'])
    need([p['comparisons'] for p in sim['passes']]==[32,48,56,60,62,63], 'comparison witness')
    need([p['timestamp_loads'] for p in sim['passes']]==[64]*6, 'load witness')
    need(sim['output']==sorted(range(64),key=lambda i:(witness['timestamps'][i],i)), 'stable witness output')
    need(len(sim['loads'])==320 and len(sim['blocks'])==31, 'later witness domain')
    base, old_audit = audit_old(sim,mapping)
    events, additions = augment(base,sim,mapping)
    ids = {e['id'] for e in events}
    validate(events,ids)
    ledger_groups = groups(events)
    controls = []
    def rejects(name, fn):
        try: fn()
        except ValueError as exc: controls.append(dict(name=name,rejected=True,reason=str(exc)))
        else: raise ValueError('control did not reject '+name)
    rejects('source-byte-change',lambda:source_map(source.replace('s.li = index as u16;','s.li = 0;',1)))
    rejects('missing-assignment-unit',lambda:validate([e for e in events if e['id'] != additions[0]['id']],ids))
    rejects('missing-initial-block-continuation',lambda:validate([e for e in events if e['id'] != additions[1921]['id']],ids))
    rejects('missing-mask-array8-transfer',lambda:validate(events[:-1],ids))
    rejects('duplicate-event-id',lambda:validate(events+[events[0]],ids))
    bad=copy.deepcopy(events);bad[-1]['bytes']=129
    rejects('129-byte-copy',lambda:validate(bad,ids))
    bad_owner=copy.deepcopy(events);bad_owner[-20]['owner']='G4'
    rejects('initial-block-owner-moved-to-G4',lambda:validate(bad_owner,ids))
    wrong=simulate(list(range(64)),U64)
    rejects('nonmaximal-timestamps-as-maximal-witness',lambda:need([p['comparisons'] for p in wrong['passes']]==[32,48,56,60,62,63],'comparison witness'))
    # Separate logical sorting checks test the independently authored cursor
    # evaluator against stable ordering, including MAX data and ineligible tails.
    rng=random.Random(20261026)
    logical=0
    for mask in [0,U64,1,1<<63,0xaaaaaaaaaaaaaaaa,0x5555555555555555]:
        for ts in [list(range(64)),list(reversed(range(64))),[U64]*64,[rng.randrange(8) for _ in range(64)]]:
            result=simulate(ts,mask)['output']
            wanted=sorted([i for i in range(64) if mask&(1<<i)],key=lambda i:(ts[i],i))
            wanted += [255]*(64-len(wanted))
            need(result==wanted,'logical ordering case')
            logical+=1
    phases=collections.defaultdict(list)
    for e in additions: phases[e['phase']].append(e)
    result=dict(schema=1,status='source-admitted G3 necessary cap violation; root decision separate',
       source_sha256=SOURCE,merge_fragment_sha256=mapping['merge_sha256'],
       baseline=cost(base),addition_phases={k:cost(v) for k,v in phases.items()},
       necessary_G3=cost(events),G3_cap=2568,over_cap=1,
       formula='ceil((32929 + 320*6 + 31*2 + 18)/16) + (384+1) = 2569 > 2568',
       full_G3_upper_built=False,G4_upper_built=False,G5_reviewed=False,
       public_file_reachability_proved=False,source_admitted_witness=True,
       selected_grammar_or_owner_changed=False,root_selection=False,
       complete_implementation_lifetime_runtime_or_GA_accepted=False,
       finite_logical_sort_cases=logical,mutation_controls=controls,
       native_compiler_runtime_UI_capture_process_inventory_Git_or_hosted=False,
       producer_code_imported_or_executed=False)
    dump('input-bindings.json',bindings)
    dump('source-map.json',mapping)
    dump('old-ledger-audit.json',old_audit)
    dump('witness.json',dict(witness,passes=sim['passes'],output=sim['output'],loads=sim['loads'],blocks=sim['blocks']))
    dump('additional-events.json',additions)
    data=dict(schema=1,source_sha256=SOURCE,scope='necessary G3 subtrace, never complete upper',
              events=events,groups=ledger_groups,totals=cost(events))
    (OUT/'necessary-ledger.json.gz').write_bytes(gzip.compress(json.dumps(data,separators=(',',':'),sort_keys=True).encode(),mtime=0))
    dump('result.json',result)
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':
    main()
