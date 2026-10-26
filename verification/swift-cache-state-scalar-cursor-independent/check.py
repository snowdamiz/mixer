#!/usr/bin/env python3
"""Reviewer-authored, standard-library-only finite source/model review.

No producer Python is imported/executed. No Rust/compiler/native/hosted harness.
The syntax matcher binds proof subjects; it supplies no OTA authority.
"""
import collections
import copy
import gzip
import hashlib
import itertools
import json
import pathlib
import random
import re
import sys

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[1]
P = ROOT / 'verification/swift-cache-state-scalar-cursor-proposal'
SOURCE = 'f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b'
SEAL = '3779a6ee9e8b38c2558e54ea4c8ae2e730ceb163b3ab154e7ee4003ef997475d'
U = (1 << 64) - 1
CHECKS = 0
INPUTS = {}


def need(ok, message):
    global CHECKS
    CHECKS += 1
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def data(path):
    path = pathlib.Path(path)
    raw = path.read_bytes()
    INPUTS[str(path.relative_to(ROOT))] = dict(bytes=len(raw), sha256=sha(raw))
    return raw


def read(path):
    return json.loads(data(path))


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def tokens(source):
    # Positioned lexical tokens, preserving literal values and every delimiter.
    pattern = r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|0x[0-9a-fA-F]+(?:u64)?|[0-9]+(?:usize|u64|u16|u8)?|[A-Za-z_]\w*|::|\.\.=|\.\.|>=|<=|==|!=|&&|\|\||<<|>>|\+=|-=|\|=|->|[^\s]'
    return [(m[0], m.start(), m.end()) for m in re.finditer(pattern, source)
            if not m[0].startswith(('//', '/*'))]


def production_tokens(source):
    ts = tokens(source)
    result = []
    at = 0
    while at < len(ts):
        if [t[0] for t in ts[at:at+7]] == ['#', '[', 'cfg', '(', 'test', ')', ']']:
            need(ts[at+7][0] == '{', 'cfg(test) block shape')
            depth = 1
            at += 8
            while depth:
                depth += (ts[at][0] == '{') - (ts[at][0] == '}')
                at += 1
        else:
            result.append(ts[at])
            at += 1
    return result


def normalized(source):
    return [t[0] for t in production_tokens(source)]


def head(side):
    pointer, index, timestamp = ('lp', 'li', 'lt') if side == 'l' else ('rp', 'ri', 'rt')
    return f'''let index = source[{pointer}]; {index} = index as u16;
               if index != u8::MAX {{ {timestamp} = u64::from_le_bytes(timestamps[index as usize]); }}'''


def independent_merge_shape():
    s = '''fn merge(c: &mut Candidate2048) {
        let eligibility = ld(c, 640);
        let (time_bytes, indices) = c.split_at_mut(512);
        let (timestamp_chunks, _) = time_bytes.as_chunks::<8>();
        let timestamps: &[[u8; 8]; 64] = timestamp_chunks.first_chunk::<64>().expect("timestamp64");
        { let output = { let mut second = u8::MAX; ['''
    for pair in range(32):
        left, right = 2*pair, 2*pair+1
        s += f'''{{ let left = if eligibility & 0x{1<<left:016x}u64 != 0 {{ {left}u8 }} else {{ u8::MAX }};
          let right = if eligibility & 0x{1<<right:016x}u64 != 0 {{ {right}u8 }} else {{ u8::MAX }};
          let lt = u64::from_le_bytes(timestamps[{left}usize]);
          let rt = u64::from_le_bytes(timestamps[{right}usize]);
          let take_left = if right == u8::MAX {{ true }} else {{ left != u8::MAX && lt <= rt }};
          if take_left {{ second = right; left }} else {{ second = left; right }}
          }}, {{ second }},'''
    s += '] }; indices[512..576].copy_from_slice(&output); }'
    for passno, width in enumerate([2, 4, 8, 16, 32], 1):
        source, destination = (512, 0) if passno % 2 else (0, 512)
        s += f'''{{ let output = {{
          let source: &[u8; 64] = indices[{source}..{source+64}].first_chunk::<64>().expect("index64");
          let mut lp: usize = 0; let mut le: usize = {width};
          let mut rp: usize = {width}; let mut re: usize = {2*width};
          let mut li: u16 = 256; let mut ri: u16 = 256;
          let mut lt: u64 = 0; let mut rt: u64 = 0;
          {{ {head('l')} {head('r')} }} ['''
        for out in range(64):
            s += '{'
            if out and out % (2*width) == 0:
                s += f'''lp = {out}; le = {out+width}; rp = {out+width}; re = {out+2*width};
                         {{ {head('l')} {head('r')} }}'''
            s += '''let take_left = if ri >= 255 { li != 256 } else { li < 255 && lt <= rt };
                    if take_left { let out = li as u8; lp += 1; if lp < le {'''
            s += head('l')
            s += '''} else { li = 256; } out }
                    else { let out = ri as u8; rp += 1; if rp < re {'''
            s += head('r')
            s += '} else { ri = 256; } out } },'
        s += f'] }}; indices[{destination}..{destination+64}].copy_from_slice(&output); }}'
    return s + '}'


def source_audit():
    seal = read(P / 'seal.json')
    need(sha((P/'seal.json').read_bytes()) == SEAL, 'producer seal identity')
    need(len(seal['members']) == 41 and seal['total_bytes'] == 3437955, 'sealed packet dimensions')
    for m in seal['members']:
        raw = data(P/m['path'])
        need(len(raw) == m['bytes'] and sha(raw) == m['sha256'], 'sealed member '+m['path'])
    for m in read(P/'input-bindings.json')['files']:
        path=P/m['snapshot'] if 'snapshot'in m else ROOT/m['path']
        raw=data(path)
        need(len(raw)==m['bytes']and sha(raw)==m['sha256'],'exact external source/selection input '+m['path'])
    source = data(P/'source/cache_state.rs.txt').decode()
    need(sha(source.encode()) == SOURCE, 'source identity')
    lo = source.index('fn merge(')
    hi = source.index('#[cfg(test)]\nstatic COMMIT_FAULT', lo)
    merge = source[lo:hi]
    need(normalized(merge) == normalized(independent_merge_shape()), 'all merge tokens match independent scalar schema')
    need('FixedArrayMergeCursor' not in source, 'no residual aggregate cursor')
    old = data(ROOT/'verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs').decode()
    need(sha(old.encode()) == '0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8', 'C3 anchor')
    row = data(ROOT/'verification/swift-cache-state-row-probe-proposal/source/cache_state.rs.txt').decode()
    need(sha(row.encode()) == 'a43397ec7cbbec398502acae5911394fced7ed8d220fee096589940eafb49fb1', 'selected G2 source anchor')
    def pieces(text, new):
        a = [text.index('// UNSELECTED SOURCE-ONLY SEEDED WIDTH1 PROPOSAL.') if new else text.index('fn merge('),
             text.index('// G2. Unselected typed-row proposal;') if new else text.index('// Shared one-pass bounded probes;'),
             text.index('// G5. Exact prior successful base+request guard proves subtraction.') if new else text.index('// The preceding checked base+request guard proves both subtractions.')]
        b = [text.index('#[cfg(test)]\nstatic COMMIT_FAULT', a[0]), text.index('    let body = w[6] as usize;', a[1]), text.index('            sq(c, 10, mask);', a[2])]
        kept = [text[:a[0]], text[b[0]:a[1]], text[b[1]:a[2]], text[b[2]:]]
        return kept, list(zip(a, b))
    kept, spans = pieces(source, True)
    old_kept, oldspans = pieces(old, False)
    need(kept == old_kept, 'all other source bytes identical to accepted C3')
    g2 = source[spans[1][0]:spans[1][1]]
    row_g2 = row[row.index('// G2. Unselected typed-row proposal;'):row.index('    let body = w[6] as usize;')]
    need(g2 == row_g2, 'exact selected G2 bytes')
    prefix = source[spans[2][0]:spans[2][1]]
    expected_prefix = '''let headroom = f.capacity - f.base - w[13];
       let mut remaining = total; let mut mask = 0; let mut destination = first_empty;
       { let (arena_words, _) = b.as_chunks::<8>(); let resident_word_base = RESIDENT.base / 8;
         let mut i = 0; while i < 64 {
           if remaining <= headroom && destination != ABSENT { break; }
           let slot_byte = c[512+i]; if slot_byte == u8::MAX { break; }
           let slot = slot_byte as u64;
           let bytes = u64::from_le_bytes(arena_words[resident_word_base+slot as usize*8+2]);
           remaining -= bytes; mask |= 1 << slot; destination = slot; i += 1;
         } }
       let feasible = destination != ABSENT && remaining <= headroom;'''
    need(normalized(prefix) == normalized(expected_prefix), 'complete G5 source shape')
    anchors = {
        'prefix-subtraction-merge-decision.json': 'e25e029dc96f6cf07968a303bba63c0dfa58929df86675b0a3f1dec8aebee8f0',
        'C3-lifetime-selection.json': 'ab2e74fa3fa7a6ff967a5c0d000d46336cc42dc5654c6b38fdce008fcafedaf4',
        'C3-remaining-work-selection.json': 'de4c117290000e9a71a5168f46cc184350bf37aa64c5714b9152bf888a08a67c',
        'G6-correction3-accounting-selection.json': 'ea00518ce5033b4651460763f1c92533d024fee32a73b182d1684afa65ef80e1',
        'row-probe-G2-selection.json': '80d78642b67d9e8164532868e56bfc2bdbeb3fcd3b2756bd9b4580c06e0123bf',
        'row-probe-G5-G6-ownership.json': '382d9017d2256dcec84b23e09f10d5618eec7796e0079f2ed5603963a0fbda03',
    }
    for name, digest in anchors.items():
        need(sha(data(ROOT/'verification/swift-semantic-adapter-root-review'/name)) == digest, 'root selected anchor '+name)
    supersession = read(P/'final-supersession.json')
    audit = dict(source_sha256=SOURCE, merge_sha256=sha(merge.encode()), independent_merge_token_count=len(normalized(merge)),
                 all320_emit_expressions_and64_seed_masks_verified=True, source_swaps=[[512,0],[0,512],[512,0],[0,512],[512,0]],
                 C3_unchanged_spans=[dict(bytes=len(z.encode()),sha256=sha(z.encode())) for z in kept],
                 changed_spans=[dict(kind=k,start_byte=a,end_byte=b,sha256=sha(source[a:b].encode())) for k,(a,b) in zip(['merge','G2','G5'],spans)],
                 G2_exact_selected_bytes=True, G6_six_calls_and_outer_merge_caller_exact=True,
                 producer_final_counts=supersession['final_G3_G4_G5'], producer_code_executed=False)
    return source, merge, g2, prefix, audit


class Trace:
    def __init__(self): self.events = []
    def s(self, *names): self.events += [dict(kind='scalar',bytes=0,operation=n) for n in names]
    def c(self, n, name, duplicate_of=None):
        e=dict(kind='copy',bytes=n,operation=name)
        if duplicate_of:e['conservative_duplicate_of']=duplicate_of
        self.events.append(e)
    def binary(self, name): self.s(name+'.left-source->operand',name+'.right-source->operand',name+'.operator',name+'.result->destination')
    def compare(self, name): self.binary(name); self.s(name+'.condition->predicate',name+'.branch')
    def statement(self, name): self.s(name+'.unit-constructor',name+'.statement-continuation')
    def index(self, name, expression, fat=False):
        self.s(*[name+'.index-expression.'+e for e in expression])
        self.s(name+'.receiver-reborrow',name+'.pointer->received-receiver')
        if fat: self.s(name+'.length->received-receiver')
        self.s(*[name+'.'+e for e in ['entry','index->bound.left','length->bound.right','bound.<','bound.branch',
                  'pointer->address.left','index->scale.left','width->scale.right','scale.*','offset->add.left',
                  'pointer->add.right','address.+','address->designated-reference','shared-loan',
                  'designated-reference->received-reference','return-control','received-reference->dereference-address','read->destination']])
    def le(self, name):
        self.c(8,name+'.full-array8-source->received-argument')
        self.s(name+'.entry',name+'.conversion',name+'.word->designated-return',name+'.return-control',name+'.word->received-destination')
    def range(self, name):
        self.s(*[name+'.'+e for e in ['start-expression->Range.start','end-expression->Range.end','Range.start->received.start','Range.end->received.end',
           'receiver-reborrow','receiver.data->received.data','receiver.len->received.len','entry','start->ordered.left','end->ordered.right','ordered.<=','ordered.branch',
           'end->upper.left','length->upper.right','upper.<=','upper.branch','data->address.left','start->address.right','address.+',
           'end->length.left','start->length.right','length.-','address->designated.data','length->designated.len','view.loan','designated.data->received.data','designated.len->received.len','return-control']])
    def fixed(self, name):
        self.s(*[name+'.'+e for e in ['receiver-reborrow','slice.data->received.data','slice.len->received.len','entry','len->bound.left','N->bound.right','bound.>=','bound.branch','data->fixed-ref','fixed.loan','reference->Some.constructor']])
        for edge in ['Option8-constructor->designated-return','Option8-designated-return->caller-received']:
            self.s(name+'.'+edge)
            self.c(8,name+'.conservative-duplicate-full-'+edge,duplicate_of=name+'.'+edge)
        self.s(name+'.first_chunk-return-control')
        self.s(name+'.Option8-caller-source->expect-received-self')
        self.c(8,name+'.conservative-duplicate-full-Option8-caller-source->expect-received-self',duplicate_of=name+'.Option8-caller-source->expect-received-self')
        self.s(*[name+'.'+e for e in ['static-message-address->message.source.data','static-message-length->message.source.len','message.data->received.message.data','message.len->received.message.len','expect.entry','Option.discriminant','Some.predicate','expect.branch','Some.pointer->designated-reference','expect.return-control','reference->received-binding','let.continuation']])
    def chunks(self, name):
        self.s(*[name+'.'+e for e in ['receiver-reborrow','slice.data->received.data','slice.len->received.len','entry','width-source->operand','width->nonzero.left','zero->nonzero.right','nonzero.!=','nonzero.branch',
          'len->quotient.left','width->quotient.right','quotient./','quotient->chunk-count','len->remainder.left','width->remainder.right','remainder.%','remainder->tail-count',
          'chunk-count->offset.left','width->offset.right','offset.*','offset->address.left','data->address.right','address.+','data->tuple.head.data','chunk-count->tuple.head.len','address->tuple.tail.data','tail-count->tuple.tail.len']])
        self.c(32,name+'.tuple-constructor->designated-return');self.c(32,name+'.tuple-designated-return->caller-received')
        self.s(name+'.return-control',name+'.received.head.data->named.data',name+'.received.head.len->named.len',name+'.discarded-full-tail',name+'.destructure.continuation')


def components():
    result = {}
    def component(name, fn):
        t = Trace(); fn(t); result[name] = t.events
    def setup(t):
        t.s(*['ld.'+e for e in ['Candidate.address','Candidate.reborrow','address->slice-source.data','2048->slice-source.len','slice.data->received.b.data','slice.len->received.b.len','640->received.at','entry','at->end.left','8->end.right','end.+','end->Range.end']])
        t.range('ld.range');t.fixed('ld.fixed');t.s('ld.reference->dereference-address','ld.array8-dereference');t.le('ld.LE');t.s('ld.return-control','ld.word->eligibility','eligibility.let-continuation')
        t.s(*['split.'+e for e in ['Candidate.address','Candidate.reborrow','address->slice-source.data','2048->slice-source.len','slice.data->received.data','slice.len->received.len','512->received.mid','entry','mid->bound.left','len->bound.right','bound.<=','bound.branch',
             'data->left.data','mid->left.len','data->address.left','mid->address.right','address.+','len->right-length.left','mid->right-length.right','right-length.-','left.loan','right.loan','left.data->tuple.left.data','left.len->tuple.left.len','right.data->tuple.right.data','right.len->tuple.right.len']])
        t.c(32,'split.tuple-constructor->designated-return');t.c(32,'split.tuple-designated-return->caller-received')
        t.s('split.return-control','split.left.data->time_bytes.data','split.left.len->time_bytes.len','split.right.data->indices.data','split.right.len->indices.len','split.destructure.continuation')
        t.chunks('timestamps.chunks');t.fixed('timestamps.fixed')
    component('G3.setup',setup)
    def seed_head(t):
        t.binary('eligibility.&');t.s('zero->eligibility-comparison.right','eligibility.!=','comparison->condition','condition->predicate','eligibility.branch',
            'eligibility.selected-arm.entry','literal-slot-or255->arm-value','arm-value->if-designated-value','eligibility.selected-arm.exit','if-designated->named-index','if-value.join','index.let-continuation')
        t.index('seed.timestamp',['literal-slot->received-index']);t.le('seed.LE');t.s('timestamp.let-continuation')
    component('G3.seed-head',seed_head)
    def choice(t, seed=False):
        t.compare('right.==255' if seed else 'right.>=255')
        t.binary('left.!=255' if seed else 'left.<255');t.s('and.short-circuit')
        t.binary('timestamp.<=')
        t.s('selected-choice-arm.entry','selected-expression->arm-value','selected-choice-arm.exit','arm-value->if-designated-value','if-value.join','if-designated->take_left','take_left.let-continuation','take_left->condition','condition->predicate','emit.branch')
    component('G3.seed-choice',lambda t:choice(t,True));component('G3.later-choice',choice)
    def later_head(t):
        t.index('head.index',['cursor->received-index']);t.s('index.let-continuation','index->u16-cast','cast.u16','cast->head');t.statement('head.assignment')
        t.compare('index.!=255');t.s('timestamp.selected-arm.entry')
        t.index('head.timestamp',['index->usize-cast','cast.usize','cast->received-index']);t.le('head.LE');t.statement('timestamp.assignment')
        t.s('timestamp.selected-arm.implicit-unit','timestamp.selected-arm.exit');t.statement('timestamp.if')
    component('G3.later-head',later_head)
    def seed_emit(t):
        t.s('element.entry','emit.selected-arm.entry','opposite-index->second');t.statement('second.assignment')
        t.s('selected-index->arm-value','emit.selected-arm.exit','arm-value->emit-if-value','emit-if.join','element.exit','emit-if-value->array-element','second-element.entry','second->array-element','second-element.exit')
    component('G4.seed-emit',seed_emit)
    def emit(t):
        t.s('element.entry','emit.selected-arm.entry','head->u8-cast','cast.u8','cast->out','out.let-continuation');t.binary('cursor.+1');t.statement('cursor.assignment')
        t.compare('cursor.<end');t.s('advance.selected-arm.entry','advance.selected-arm.implicit-unit','advance.selected-arm.exit');t.statement('advance.if')
        t.s('out->emit-arm-value','emit.selected-arm.exit','arm-value->if-value','emit-if.join','element.exit','if-value->array-element')
    component('G4.later-emit',emit)
    component('G4.source-view',lambda t:(t.range('source.range'),t.fixed('source.fixed')))
    def output(t):
        t.c(64,'array-constructor->block-designated');t.c(64,'block-designated->output');t.s('output.let-continuation');t.range('destination.range')
        t.s(*['copy.'+e for e in ['receiver-reborrow','destination.data->received.data','destination.len->received.len','output.array-address','output.reborrow','output.address->coerced.data','64->coerced.len','coerced.data->received.source.data','coerced.len->received.source.len','entry','dest.len->bound.left','source.len->bound.right','length.==','length.branch']])
        t.c(64,'copy.output64-source->actual-Candidate64-destination');t.s('copy.implicit-unit','copy.return-control');t.statement('copy.statement');t.statement('outer-output-block')
    component('G4.output',output)
    def prefix_body(t):
        t.compare('while.i<64');t.s('while.body.entry');t.binary('remaining.<=headroom');t.s('headroom.and-short-circuit');t.binary('destination.!=ABSENT');t.s('headroom.condition->predicate','headroom.branch');t.statement('headroom.if')
        t.index('Candidate.index',['512->plus.left','i->plus.right','index.+','index-result->received-index']);t.s('slot_byte.let-continuation');t.compare('slot_byte.==255');t.statement('sentinel.if')
        t.s('slot_byte->u64-cast','cast.u64','cast->slot','slot.let-continuation')
        t.index('arena.index',['resident-base->plus.left','slot->usize-cast','cast.usize','cast->multiply.left','8->multiply.right','multiply.*','product->nested-plus.right','nested-plus.+','nested-sum->outer-plus.left','2->outer-plus.right','outer-plus.+','sum->received-index'],True)
        t.le('bytes.LE');t.s('bytes.let-continuation');t.binary('remaining.-bytes');t.statement('remaining.assignment')
        t.s('mask->or.left','1->shift.left','slot->shift.right','shift.<<','shift-result->or.right','or.|','or-result->mask');t.statement('mask.assignment')
        t.s('slot->destination');t.statement('destination.assignment');t.binary('i.+1');t.statement('i.assignment');t.s('while.body.implicit-unit','while.back-control')
    component('G5.body',prefix_body)
    def prelude(t):
        t.s('f->capacity-address','capacity.address','capacity->first-minus.left','f->base-address','base.address','base->first-minus.right','first-minus.-','partial->second-minus.left')
        t.index('request.index',['13->received-index']);t.s('second-minus.-','headroom-result->binding','headroom.let-continuation','total->remaining','remaining.let-continuation','0->mask','mask.let-continuation','first_empty->destination','destination.let-continuation','prefix-block.entry')
        t.chunks('arena.chunks');t.s('RESIDENT->base-address','base.address','base->divide.left','8->divide.right','divide./','quotient->resident_word_base','resident_word_base.let-continuation','0->i','i.let-continuation')
    component('G5.prelude',prelude)
    def terminal(t):
        t.compare('final.while-test');t.s('final.false-branch','while.unit','while.continuation','prefix-block.unit','prefix-block.exit',
          'headroom-break.arm-entry','headroom-break.control','headroom-break.scope-exit','sentinel-break.arm-entry','sentinel-break.control','sentinel-break.scope-exit')
        t.binary('feasible.destination!=ABSENT');t.s('feasible.and-short-circuit');t.binary('feasible.remaining<=headroom');t.s('feasible.let-continuation')
    component('G5.terminal-union',terminal)
    return result


def cost(events):
    s = sum(e['kind']=='scalar' for e in events)
    c = sum(e['kind']=='copy' for e in events)
    return dict(scalars=s,copies=c,scalar_groups=(s+15)//16,groups=(s+15)//16+c)


def independent_upper(cs):
    recipes = {
      'G3':[('G3.setup',1),('G3.seed-head',64),('G3.seed-choice',32),('G3.later-head',320),('G3.later-choice',320)],
      'G4':[('G4.seed-emit',32),('G4.source-view',5),('G4.later-emit',320),('G4.output',6)],
      'G5':[('G5.prelude',1),('G5.body',64),('G5.terminal-union',1)]}
    exact = {'G3': [], 'G4': [], 'G5': []}
    for p in range(5):
        exact['G3'] += [(f'p{p}.head.{n}', ['literal->named-head','let.continuation']) for n in ['li','ri','lt','rt']]
        exact['G4'] += [(f'p{p}.pointer.{n}', ['literal->named-pointer','let.continuation']) for n in ['lp','le','rp','re']]
    exact['G3'] += [(f'initial-head-block.{i}', ['scope.entry','implicit-unit','scope.exit-continuation']) for i in range(31)]
    exact['G3'] += [(f'exhaustion.{i}', ['256->head','assignment.unit','assignment.continuation']) for i in range(62)]
    exact['G4'] += [('second.initializer',['MAX255->second','let.continuation'])]
    exact['G4'] += [(f'output-block.{i}',['outer.entry','array-constructor.entry','array-constructor.control','inner-output-block.exit']) for i in range(6)]
    exact['G4'] += [(f'reset.{i}.{n}', ['literal->pointer','assignment.unit','assignment.continuation']) for i in range(26) for n in ['lp','le','rp','re']]
    exact['G4'] += [('merge.return',['callee.implicit-unit','callee.return-control'])]
    all_events=[]; uppers={};groups=[]
    for owner in ['G3','G4','G5']:
        es=[]
        def add(site, seq):
            for j,e in enumerate(seq): es.append(dict(e,owner=owner,site=site,id=f'{owner}/{site}/{j}'))
        for name,repeat in recipes[owner]:
            for i in range(repeat):add(name+'/'+str(i),cs[name])
        for site,labels in exact[owner]:add(site,[dict(kind='scalar',bytes=0,operation=x)for x in labels])
        all_events+=es;uppers[owner]=cost(es)
        scalar=[e['id']for e in es if e['kind']=='scalar']
        groups += [dict(owner=owner,kind='scalar',events=scalar[i:i+16])for i in range(0,len(scalar),16)]
        groups += [dict(owner=owner,kind='copy',bytes=e['bytes'],events=[e['id']])for e in es if e['kind']=='copy']
    validate_partition(all_events,groups)
    for n,cap in {'G3':2568,'G4':768,'G5':640}.items():need(uppers[n]['groups']<=cap,n+' complete upper cap')
    return uppers,recipes,all_events,groups


def validate_partition(events,groups):
    byid={e['id']:e for e in events};need(len(byid)==len(events),'unique event identifiers')
    used=[]
    for g in groups:
        es=[byid[i]for i in g['events']];need(es and all(e['owner']==g['owner']for e in es),'same owner/nonempty')
        if g['kind']=='scalar':need(len(es)<=16 and all(e['kind']=='scalar' and e['bytes']==0 for e in es),'at most16 scalar primitives')
        else:need(len(es)==1 and es[0]['kind']=='copy' and 0<es[0]['bytes']<=128 and es[0]['bytes']==g['bytes'],'complete independent bounded copy')
        used += g['events']
    need(collections.Counter(used)==collections.Counter(byid.keys()),'exact-once coverage')


def logical_merge(ts, eligible):
    values=[];loads=[64];selected=[]
    for i in range(0,64,2):
        a=i if i in eligible else 255;b=i+1 if i+1 in eligible else 255
        values.extend([a,b] if b==255 or a!=255 and ts[i]<=ts[i+1] else [b,a])
    for width in [2,4,8,16,32]:
        destination=[];real_reads=0;index_reads=0;exhaustions=0;blocks=0
        for start in range(0,64,2*width):
            end=start+2*width;lp=start;rp=start+width;le=rp;re_=end;blocks+=1
            li=values[lp];ri=values[rp];index_reads+=2
            lt=ts[li] if li!=255 else 0;rt=ts[ri] if ri!=255 else 0;real_reads+=(li!=255)+(ri!=255)
            while len(destination)<end:
                take=li!=256 if ri>=255 else li<255 and lt<=rt
                if take:
                    need(li!=256,'left256 cannot emit');destination.append(li);lp+=1
                    if lp==le:li=256;exhaustions+=1
                    else:
                        li=values[lp];index_reads+=1
                        if li!=255:lt=ts[li];real_reads+=1
                else:
                    need(ri!=256,'right256 cannot emit');destination.append(ri);rp+=1
                    if rp==re_:ri=256;exhaustions+=1
                    else:
                        ri=values[rp];index_reads+=1
                        if ri!=255:rt=ts[ri];real_reads+=1
            need(lp==le and rp==re_,'exact exhausted run endpoints')
        need(index_reads==64 and real_reads<=64,'universal per-pass head-read bound witnessed')
        values=destination;loads.append(real_reads);selected.append(dict(width=width,index_reads=index_reads,real_reads=real_reads,exhaustions=exhaustions,blocks=blocks))
    expected=sorted(eligible,key=lambda i:(ts[i],i))+[255]*(64-len(eligible))
    need(values==expected,'independent stable tuple-key oracle')
    return values,loads,selected


def logical_prefix(order, sizes, occupied, headroom, destination, checked):
    total=0
    for i in occupied:
        need(0<sizes[i]<=U,'positive G2 admitted occupied size')
        total+=sizes[i];need(total<=U,'G2 sum does not overflow')
    remaining=total;mask=0;trace=[];consumed=set()
    for i in range(64):
        if remaining<=headroom and destination!=U:break
        trace.append(('Candidate',512+i));slot=order[i]
        if slot==255:break
        trace.append(('resident',slot,2))
        need(slot in occupied and slot not in consumed,'unique eligible physical slot')
        size=sizes[slot]
        if checked and remaining<size:return dict(reason=13,trace=trace)
        need(remaining>=size,'ordinary subtraction universal invariant')
        remaining-=size;mask|=1<<slot;destination=slot;consumed.add(slot)
        need(remaining==sum(sizes[j]for j in occupied-consumed),'remaining exact unconsumed sum')
    return dict(reason=0,remaining=remaining,mask=mask,destination=destination,feasible=destination!=U and remaining<=headroom,trace=trace)


def finite():
    merges=prefixes=0;rng=random.Random(2026102601)
    for n in range(6):
        for ts0 in itertools.product([0,1,U],repeat=n):
            ts=list(ts0)+[0]*(64-n)
            for mask in range(1<<n):
                logical_merge(ts,{i for i in range(n)if mask>>i&1});merges+=1
    families=[[0]*64,[U]*64,list(range(64)),list(reversed(range(64))),[int(f'{i:06b}'[::-1],2)for i in range(64)],[0 if i%2 else U for i in range(64)],[rng.getrandbits(64)for _ in range(64)]]
    masks=[0,U,0xaaaaaaaaaaaaaaaa,0x5555555555555555]+[(1<<i)-1 for i in range(65)]+[rng.getrandbits(64)for _ in range(96)]
    for ts in families:
        for mask in masks:
            eligible={i for i in range(64)if mask>>i&1};order,_,_=logical_merge(ts,eligible);merges+=1
            # Additional occupied rows are pinned: identities and pin nonce values
            # cannot change this physical-slot invariant or the subtraction.
            occupied=eligible|{i for i in range(64)if i%3==0};sizes=[1+rng.randrange(256)if i in occupied else 0 for i in range(64)]
            for headroom in [0,sum(sizes)//2,sum(sizes),U]:
                for destination in [0,U]:
                    a=logical_prefix(order,sizes,occupied,headroom,destination,False);b=logical_prefix(order,sizes,occupied,headroom,destination,True)
                    need(a==b,'checked/ordinary values and exact lazy read sequence');prefixes+=1
    for sizes,occupied in [([U]+[0]*63,{0}),([U//64]*63+[U-63*(U//64)],set(range(64)))]:
        order,_,_=logical_merge([U]*64,occupied)
        for headroom in [0,1,U//2,U]:
            for dest in [U,63]:
                need(logical_prefix(order,sizes,occupied,headroom,dest,False)==logical_prefix(order,sizes,occupied,headroom,dest,True),'full-u64 boundary equality');prefixes+=1
    return dict(merge_cases=merges,prefix_comparisons=prefixes,universal_proof_replaced_by_finite_cases=False)


def lexical(source, start, end, sizes):
    ts=production_tokens(source[start:end]);stack=[];ends={};scope_at={}
    for i,(token,_,_)in enumerate(ts):
        scope_at[i]=stack[-1]if stack else None
        if token=='{':stack.append(i)
        elif token=='}':
            need(bool(stack),'balanced scope closes');ends[stack.pop()]=i
    need(not stack,'balanced lexical scopes')
    rows=[]
    for i,(token,a,_)in enumerate(ts):
        if token!='let':continue
        j=i+1
        if ts[j][0]=='mut':j+=1
        if ts[j][0] in ['[','(']:
            close=']'if ts[j][0]=='['else ')';depth=1;k=j+1
            while depth:
                depth+=(ts[k][0]==ts[j][0])-(ts[k][0]==close);k+=1
            names=[x[0]for x in ts[j+1:k-1]if re.fullmatch(r'[A-Za-z_]\w*',x[0])and x[0]!='_']
        elif ts[j][0]=='Some':names=[ts[j+2][0]]
        else:names=[ts[j][0]]
        scope=scope_at[i];need(scope is not None,'let has lexical owner block')
        for name in names:
            need(name in sizes,'known actual local size '+name)
            b=ts[ends[scope]][1]
            rows.append(dict(name=name,id=f'{name}@{start+a}',bytes=sizes[name],birth=start+a,end=start+b,birth_line=source[:start+a].count('\n')+1,end_line=source[:start+b].count('\n')+1,last_use_retirement=False))
    points={r['birth']for r in rows}|{r['end']for r in rows}
    peak=max((sum(r['bytes']for r in rows if r['birth']<=p<r['end']),p)for p in points)
    return rows,dict(bytes=peak[0],at_byte=peak[1],live=[r['id']for r in rows if r['birth']<=peak[1]<r['end']])


def lifetime(source, merge, g2, prefix):
    merge_sizes=dict(eligibility=8,time_bytes=16,indices=16,timestamp_chunks=16,timestamps=8,output=64,second=1,left=1,right=1,lt=8,rt=8,take_left=1,source=8,lp=8,le=8,rp=8,re=8,li=2,ri=2,index=1,out=1)
    lo=source.index('fn merge(');rows,peak=lexical(source,lo,lo+len(merge),merge_sizes)
    need(len(rows)==1879 and peak['bytes']==191,'exact production merge named owners/lexical peak')
    supplied=read(P/'whole-lifetimes.json')['merge_named_places']
    need({(r['id'],r['birth'],r['end'],r['bytes'])for r in rows}=={(r['id'],r['birth_byte'],r['lexical_end_byte'],r['bytes'])for r in supplied},'independent positioned merge lexical mapping')
    # Complete G2 names include actual borrowed array-pattern owners and scopes.
    g2_names=['arena_words','resident_chunks','resident_rows','pin_chunks','pin_rows','time_bytes','index_bytes','timestamp_chunks','timestamp_words','record_kind','requested_function','release_nonce','prior_count','prior_total','prior_pins','next_nonce','configured_slots','configured_pins','configured_entry','resident_limit','pin_limit','eligibility','slot','row','occupied_le','function_le','bytes_le','pins_le','last_used_le','reserved6_le','reserved7_le','occupied','function','bytes','pins','sum','pin','entry_le','nonce_le','entry','nonce','back_row','back_occupied_le','back_pins_le']
    g2_sizes={n:8 for n in g2_names}
    for n in ['arena_words','resident_chunks','pin_chunks','time_bytes','index_bytes','timestamp_chunks']:g2_sizes[n]=16
    g2lo=source.index('// G2. Unselected typed-row proposal;');g2rows,g2peak=lexical(source,g2lo,g2lo+len(g2),g2_sizes)
    g2life=read(ROOT/'verification/swift-cache-state-row-probe-independent/G2-lifetimes.json')
    need(g2life['Control_peak']==1220 and g2life['block_named_Control']==232,'selected G2 lifetime maxima')
    # Prefix is within the actual event5 branch, so parse with an added brace.
    ps=dict(headroom=8,remaining=8,mask=8,destination=8,arena_words=16,resident_word_base=8,i=8,slot_byte=1,slot=8,bytes=8,feasible=1)
    prows,ppeak=lexical('{'+prefix+'}',0,len(prefix)+2,ps)
    need(len(prows)==11 and sum(ps.values())==82,'complete prefix named inventory')
    old=read(ROOT/'verification/swift-semantic-adapter-root-review/C3-lifetime-selection.json')
    addendum=read(ROOT/'verification/swift-cache-state-c3-lifetime-independent/coverage-addendum.json')
    oldphases=read(ROOT/'verification/swift-cache-state-c3-lifetime-accounting/phases.json')
    oldnames=read(ROOT/'verification/swift-cache-state-c3-lifetime-accounting/named-places.json')
    need(old['whole_role_union_accepted'] and not old['original_producer_exact_phase_completeness_accepted'],'actual root lifetime selection, not original incomplete claim')
    need(len(addendum['schedules'])==18 and old['whole_role_union']==29344,'all selected supplemental schedules inherited')
    # One complete active caller inventory, not an unbounded caller stack claim.
    caller={'Progress':144,'cache_inputs.arguments':24,'cache_inputs.received':24,'cache_walk.arguments':16,'cache_walk.received':16,'fixture.source':8,'fixture.received':8,'outer.arena.reference':8,'Loan':16,'StepBudget':16,'semantic.arguments':48,'semantic.received':48,'w-and-f':16,'eleven.outer-scalars':88,'body':8,'miss.cell':8,'merge.argument-source':8,'merge.received-c':8}
    need(sum(caller.values())==512,'full merge caller source/received inventory')
    # All endpoint roles below are deliberately unioned, even when sequential.
    # Reviewer-decomposed primitive API capacity unions. References are object
    # descriptors, never additional pointed-to payloads. A source16 plus
    # received16 slice bound also covers the actual reborrow8 + fat receiver16.
    api={
      'split_at_mut':dict(receiver_source_and_received=32,mid_source_and_received=16,bound_operands_and_bool=17,
          two_slice_sources=32,address_operands_result=24,length_operands_result=24,complete_tuple_constructor_designated_received=96,two_loan_sources=16),
      'as_chunks':dict(receiver_source_and_received=32,width_operand=8,nonzero_operands_bool=17,
          quotient_operands_result=24,remainder_operands_result=24,chunk_and_tail_counts=16,
          offset_operands_result=24,address_operands_result=24,complete_tuple_constructor_designated_received=96),
      'range-fixed-expect':dict(Range_source_and_received=32,range_slice_receiver_source_received=32,
          bounds_operands_and_bool=17,address_operands_result=24,length_operands_result=24,view_designated_received=32,
          fixed_slice_receiver_source_received=32,fixed_length_operands_bool=17,complete_Option8_constructor_designated_received=24,
          expect_received_self=8,message_source_and_received=32,discriminant_and_bool=9,fixed_reference_designated_received=16),
      'Index-and-LE':dict(index_expression_sources=24,index_expression_received_operands=24,index_expression_results=24,
          receiver_source_received=32,index_source_received=16,bound_operands_bool=17,address_operands_result=24,scale_operands_result=24,
          reference_designated_received=16,LE_full_array8_source_received=16,LE_word_designated_received=16,assignment_source_and_target_address=16),
      'copy_from_slice':dict(Range_source_received=32,receiver_source_received=32,bound_operands_bool=17,
          address_operands_result=24,length_operands_result=24,view_designated_received=32,destination_descriptor_source_received=32,
          source_descriptor_source_received=32,length_equality_operands_bool=17),
      'primitive':dict(left_and_right_source_operands=16,left_and_right_received_operands=16,result=8,condition_source_received=2,retained_shortcircuit_operand=8),
    }
    expected_api={'split_at_mut':257,'as_chunks':265,'range-fixed-expect':299,'Index-and-LE':249,'copy_from_slice':242,'primitive':50}
    need({n:sum(v.values())for n,v in api.items()}==expected_api,'audited actual API source/received/designated capacities')
    # Supplement is tied to actual source nested boundaries, not generic margin:
    # ld(c,640) argument sources/received b16+at8 remain distinct from its range
    # endpoint; actual at+8 retains its operand/result places; first_chunk/expect
    # full Option received self remains separate; dereference has its own address.
    ld_nested={'ld.b.argument-source':16,'ld.at.argument-source':8,'ld.b.received-parameter':16,'ld.at.received-parameter':8,
               'ld.at-plus8.left-source':8,'ld.at-plus8.right-source':8,'ld.at-plus8.result':8,
               'ld.at-plus8.left-received':8,'ld.at-plus8.right-received':8,
               'expect.Option8.source-for-self':8,'expect.Option8.received-self':8,
               'fixed-reference.dereference-source-address':8,'fixed-reference.dereference-received-address':8}
    need(sum(ld_nested.values())==120,'named forwarding/source endpoint inventory120')
    phases=[]
    for n,endpoint in expected_api.items():
        places=dict(caller=512,merge_named_lexical_peak=191,array_constructor64=64,array_designated64=64,API_endpoint_union=endpoint,**ld_nested)
        value=sum(places.values());need(value<=1280,'new merge logical Control allowance '+n)
        phases.append(dict(id='merge.'+n,Control=value,Wire=24,Setup=80,Report=0,places=places))
    # RESIDENT is a complete Region24 source in the actual prefix base expression.
    for n in ['as_chunks','Index-and-LE','primitive']:
        places=dict(semantic_caller_after_body=488,miss_cell=8,prefix_named_union=82,RESIDENT_Region_source=24,API_endpoint_union=expected_api[n])
        phases.append(dict(id='prefix.'+n,Control=sum(places.values()),Wire=24,Setup=80,Report=0,places=places))
    phases.append(dict(id='G6.final-stores',Control=953,Wire=24,Setup=80,Report=0,places=dict(semantic_caller_after_body=488,miss_cell=8,live_prefix_outer_locals=33,complete_sq_st_endpoint_union=424)))
    new_peaks=dict(Control=max(1220,1201,*[p['Control']for p in phases]),Wire=152,Setup=160,Report=2688)
    allowances=dict(Control=1280,Wire=256,Setup=256,Report=2896)
    need(all(new_peaks[n]<=allowances[n]for n in allowances),'whole fixed role allowances')
    need(24656+sum(allowances.values())==29344,'fixed whole role union')
    # Whole Result capacities and Candidate remain inherited independently of the
    # active variant. Preserve the original selected rows and 18 corrections.
    result_places=[dict(p,phase=phase['id'])for phase in oldphases['phases']for p in phase['added_places']if 'Result'in p['place']or 'Result'in p['endpoint']]
    need(sum(p['bytes']==488 for p in result_places)==2,'complete early public Err488 source and immediate received Result488 retained')
    need(sum(p['bytes']==256 and 'inherited_aggregate_Result_slot'in p['place']for p in result_places)==5,'all five inherited232 plus added256 slots retained as whole488')
    need(any(p['bytes']==2048 and 'candidate'in p['id']for p in oldnames['places']),'one inherited Candidate2048 object retained')
    return dict(scope='authored source logical objects and explicit API endpoints only',merge_named_owners=rows,merge_named_peak=peak,G2_named_owners=g2rows,G2_named_peak=g2peak,G2_selected_lifetimes_retained=g2life,
                prefix_named_owners=prows,prefix_named_peak=ppeak,caller=caller,API_endpoint_unions=api,forwarding_supplement=ld_nested,phases=phases,added_peaks=new_peaks,allowances=allowances,
                inherited_role_union=24656,whole_role_union=29344,reserved=41984,ceiling=65536,unassigned_margin_used=0,
                inherited_complete_result_places=result_places,inherited_18_schedules=addendum['schedules'],inherited_original_phases_count=len(oldphases['phases']),
                inherited_Candidate2048_is_one_object=True,new_payload_bytes=0,no_last_use_retirement=True,machine_stack_or_libstd_claim=False)


def inherited_niche_reconciliation():
    """Bind the already selected scalar-niche grammar, not a new copy mandate."""
    scoped_custody=[]
    for dirname,digest,names in [
        ('swift-cache-state-row-probe-proposal','8d3317005e5db2b6114a9bd2be3c40682920f20041a5b46bd22d50ae929aab7f',['components.json']),
        ('swift-cache-state-row-probe-independent','4918dfa723161e9cead7087e066baf8021efe64a9a27dee67a6e8518f61c365e',['correction-addendum.json']),
        ('swift-cache-state-g6-complete','c806b2967e37978403641c0172f3d70013b1e74c0d28128236f26fb618812597',['operation-templates.json','source-model.json']),
        ('swift-cache-state-c3-remaining-work-accounting','90eb895fe6c34dc68c3bb7826b0852f49926375f80c510020f4f7ed454ad8cb3',['templates.json']),
    ]:
        packet=ROOT/'verification'/dirname
        seal=read(packet/'seal.json');need(sha((packet/'seal.json').read_bytes())==digest,'selected scoped seal '+dirname)
        for name in names:
            path=packet/name;relative=str(path.relative_to(ROOT));member=next(m for m in seal['members']if m['path']==relative)
            raw=data(path);need(sha(raw)==member['sha256']and len(raw)==member['bytes'],'selected exact niche template '+relative)
            scoped_custody.append(dict(path=relative,sha256=member['sha256'],selected_seal_sha256=digest))
    selected=read(ROOT/'verification/swift-cache-state-row-probe-proposal/components.json')['templates']['prelude']
    labels=[e['operation']for e in selected]
    required=['complete Option<&array>8 source pointer -> caller received Option8',
              'caller Option pointer -> expect received self',
              'static expect text address -> message.data source',
              'static expect text length -> message.len source',
              'message.data -> expect received message.data',
              'message.len -> expect received message.len']
    for label in required:need(labels.count(label)==3,'all3 selected G2 endpoint labels '+label)
    corr=read(ROOT/'verification/swift-cache-state-row-probe-independent/correction-addendum.json')
    edges=corr['components']['prelude']['scalar_edges']
    option_returns=[x for x in edges if x.endswith('Option.pointer.constructor->designated-return')]
    need(len(option_returns)==3,'G2 selected Option8 designated-return corrections')
    life=read(ROOT/'verification/swift-cache-state-row-probe-independent/G2-lifetimes.json')
    row=next(p for p in life['phases']if p['id']=='view.first_chunk_expect')
    for n,b in {'first_chunk_expect.Option_pointer_constructor':8,'first_chunk_expect.Option_pointer_designated_return':8,
                'first_chunk_expect.Option_pointer_received':8,'first_chunk_expect.expect_self_argument_source':8,
                'first_chunk_expect.expect_self_received':8,'first_chunk_expect.expect_message_source':16,
                'first_chunk_expect.expect_message_received':16}.items():need(row['places'][n]==b,'G2 exact complete lifetime endpoint '+n)
    g6=read(ROOT/'verification/swift-cache-state-g6-complete/operation-templates.json')
    ld=next(t for t in g6['templates']if t['name']=='ld Candidate/literal')
    g6labels=[e['operation']for e in ld['operations']]
    g6required=['complete Option<&array8> pointer -> caller received Option pointer',
                'caller received Option pointer -> expect received self',
                'static expect text address -> message.data source','static expect text length -> message.len source',
                'message.data -> expect received message.data','message.len -> expect received message.len']
    need(all(x in g6labels for x in g6required),'unchanged G6 full niche and message endpoints')
    remaining=read(ROOT/'verification/swift-cache-state-c3-remaining-work-accounting/templates.json')
    ldremain=next(t for t in remaining['templates']if t['name']=='ld Candidate/literal')
    remainlabels=[e['operation']for e in ldremain['operations']]
    need('complete Option reference8 source -> received Option8'in remainlabels and 'received Option8 -> expect received self'in remainlabels,'unchanged remaining-work niche endpoints')
    need(all(x in remainlabels for x in ['expect message address -> source.data','expect message length -> source.len','message.data -> received message.data','message.len -> received message.len']),'unchanged remaining-work full message endpoints')
    model=read(ROOT/'verification/swift-cache-state-g6-complete/source-model.json')
    need('Option<u64>/Option<usize>'in model['complete_Option_rule'],'selected full16 Option rule preserved')
    return dict(rule='selected pointer-niche Option8 transfers remain complete8-byte scalar pointer events; Option16 remains complete copy. Extra Option8 payload charges in new reviewer upper deliberately duplicate existing scalar pointer events; they are optional conservative charges, not missing source events or a changed grammar.',scoped_selected_template_custody=scoped_custody,
                selected_G2_upper=dict(scalars=26491,copies=838,groups=2494),selected_G2_lifetime_peak=1220,
                G2_message_and_niche_labels=required,G2_designated_return_corrections=option_returns,G2_full_lifetime_row=row,
                inherited_G6_niche_and_message_labels=g6required,inherited_remaining_work_niche_and_message_labels=[x for x in remainlabels if 'Option8'in x or 'message'in x],
                whole_Control1250_is_merge_forwarding_upper_not_G2_growth=True,source_model_complete_Option_rule=model['complete_Option_rule'])


def main():
    source,merge,g2,prefix,audit=source_audit()
    cs=components();uppers,recipes,events,groups=independent_upper(cs)
    life=lifetime(source,merge,g2,prefix)
    inherited_niche=inherited_niche_reconciliation()
    combined_groups=94+2494+sum(v['groups']for v in uppers.values())+512+178
    need(combined_groups==7048 and combined_groups<=7680,'combined production work within same prepaid semantic7680')
    need(7680+471==8151 and 8151<=8192,'unchanged combined prepaid source charge fits preflight8192')
    tests=finite()
    mutations=[]
    def rejects(name,fn):
        try:fn()
        except (ValueError,KeyError)as exc:mutations.append(dict(name=name,rejected=True,reason=str(exc)))
        else:raise ValueError('mutation unexpectedly admitted '+name)
    rejects('source changed sentinel',lambda:need(normalized(merge.replace('li = 256;','li = 255;',1))==normalized(independent_merge_shape()),'source/sentinel mismatch'))
    rejects('source changed source-array swap',lambda:need(normalized(merge.replace('indices[512..576].first_chunk','indices[0..64].first_chunk',1))==normalized(independent_merge_shape()),'source-view mismatch'))
    rejects('MAX used as eligibility',lambda:need(logical_merge([U]*64,set(range(64)))[0]==[255]*64,'timestamp MAX is ordinary data'))
    rejects('unstable ties',lambda:need(logical_merge([0]*64,set(range(64)))[0]==list(reversed(range(64))),'stable ascending physical slots'))
    rejects('duplicate physical victim',lambda:logical_prefix([0,0]+[255]*62,[1,1]+[0]*62,{0,1},0,U,False))
    rejects('stale size violates occupied sum',lambda:logical_prefix([0]+[255]*63,[2]+[0]*63,set(),0,U,False))
    bad=copy.deepcopy(groups);next(g for g in bad if g['kind']=='scalar'and len(g['events'])==16)['events'].append(events[0]['id']);rejects('17scalar group',lambda:validate_partition(events,bad))
    bad=copy.deepcopy(events);next(e for e in bad if e['kind']=='copy')['bytes']=129;rejects('129byte copy',lambda:validate_partition(bad,groups))
    rejects('missing covered event',lambda:validate_partition(events[1:],groups))
    bad=copy.deepcopy(events);bad[0]['owner']='G4';rejects('cross-owner work transfer',lambda:validate_partition(bad,groups))
    rejects('last-use lexical retirement',lambda:need(all(r['end']>r['birth']and not r.get('last_use_retirement')for r in [dict(life['merge_named_owners'][0],last_use_retirement=True)]),'lexical scope must survive last use'))
    rejects('active Err variant32 only',lambda:need(32==488,'complete public Result488 capacity'))
    rejects('fat receiver narrowed to pointer8',lambda:need(8>=24,'fat reborrow8 plus slice16 remain distinct'))
    rejects('original C3 inventory alone authorizes whole proof',lambda:need(False,'root selected18 supplementary schedules required'))
    write('source-audit.json',audit)
    write('components.json',dict(templates=cs,costs={n:cost(es)for n,es in cs.items()}))
    duplicates=[e for e in events if 'conservative_duplicate_of'in e]
    need(len(duplicates)==21,'explicit optional21 duplicate niche payload charges')
    write('independent-upper.json',dict(bounds=uppers,recipes=recipes,producer_exact_totals_accepted=False,all_path_upper=True,ownership_changed=False,
        exact_once_charge_partition=True,exact_once_actual_source_event_claim=False,conservative_duplicate_niche_payload_charges=duplicates,source=SOURCE))
    write('inherited-niche-reconciliation.json',inherited_niche)
    write('whole-lifetimes.json',life)
    with gzip.GzipFile(filename=str(OUT/'complete-upper-ledger.json.gz'),mode='wb',mtime=0)as f:f.write(json.dumps(dict(events=events,groups=groups),separators=(',',':')).encode())
    write('finite-checks.json',tests);write('negative-controls.json',mutations)
    result=dict(schema=1,status='scoped independent source/model acceptance with conservative accounting correction; root selection required',source_sha256=SOURCE,producer_seal_sha256=SEAL,
       independent_complete_uppers=uppers,producer_exact_totals_selected=False,whole_added_peaks=life['added_peaks'],whole_role_union=29344,
       combined_production_G1_to_G7=combined_groups,semantic_prepaid=7680,combined_prepaid=8151,preflight_cap=8192,
       inherited_G2=2494,inherited_G6_production=512,inherited_G6_private=514,selected_niche_grammar_preserved=True,extra_niche_payload_charges_are_optional_duplicates=True,
       universal_merge_and_subtraction_source_argument_reviewed=True,
       finite=tests,negative_controls=len(mutations),checks=CHECKS,optimized=bool(sys.flags.optimize),producer_code_imported_or_executed=False,
       compiler_product_runtime_native_UI_capture_process_inventory_Git_or_hosted_actions=False,public_File_reachability_proved=False,implementation_selected=False,root_selection_required=True,GA_qualified=False)
    write('result-optimized.json'if sys.flags.optimize else'result.json',result)
    write('input-bindings.json',dict(files=INPUTS,input_tree_digest=sha(json.dumps(INPUTS,sort_keys=True,separators=(',',':')).encode()),source_model_only=True))
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
