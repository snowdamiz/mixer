#!/usr/bin/env python3
"""Independent source-only audit. Producer JSON is data; producer Python is never loaded."""
import copy, gzip, hashlib, json, math, pathlib, random, struct, sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=pathlib.Path(__file__).resolve().parent
P=ROOT/'verification/swift-cache-state-row-probe-proposal'
SEAL='8d3317005e5db2b6114a9bd2be3c40682920f20041a5b46bd22d50ae929aab7f'
SOURCE='a43397ec7cbbec398502acae5911394fced7ed8d220fee096589940eafb49fb1'
U=(1<<64)-1

def need(ok,msg):
    if not ok: raise ValueError(msg)
def sha(b): return hashlib.sha256(b).hexdigest()
def read(n): return json.loads((P/n).read_text())
def zipped(n): return json.loads(gzip.decompress((P/n).read_bytes()))
def write(n,x): (OUT/n).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')

# Reviewer-authored hand equations, matched to the audited source grammar.
# Tuple values are scalar fields; payload arrays and Option<u64> are distinct copies.
EXPECTED={
'mask-store':(48,2),'pin-init':(1,0),'pin-test':(6,0),
'pin.empty-first':(73,2),'pin.empty-invalid-nonce':(67,3),'pin.empty-later':(70,2),
'pin.invalid-backlink0':(125,4),'pin.invalid-backlink1':(135,5),
'pin.invalid-header0':(68,3),'pin.invalid-header1':(73,3),'pin.invalid-header2':(78,3),
'pin.live-nonrelease':(144,4),'pin.live-release-match':(153,4),'pin.live-release-other':(149,4),
'post.fail0.0':(15,1),'post.fail1.0':(23,1),'post.fail1.1':(28,1),
'post.fail2.0':(36,1),'post.fail2.1':(42,1),'post.fail2.2':(48,1),'post.fail2.3':(53,1),'post.success':(46,0),
'prelude':(397,0),'resident-test':(6,0),
'resident.duplicate':(174,8),'resident.empty-first':(177,7),'resident.empty-later':(174,7),
'resident.invalid-body0':(134,7),'resident.invalid-body1':(139,7),'resident.invalid-body2':(143,7),
'resident.invalid-empty0':(130,7),'resident.invalid-empty1':(135,7),'resident.invalid-empty2':(139,7),
'resident.invalid-header0':(91,5),'resident.invalid-header1':(96,5),'resident.invalid-header2':(107,6),'resident.invalid-header3':(117,7),
'resident.occupied-eligible':(208,8),'resident.occupied-match':(210,8),'resident.occupied-match-eligible':(217,8),'resident.occupied-other':(201,8),'resident.overflow':(154,8),
'tail-body':(33,1),'tail-test':(6,0)}
RES_OK=['empty-first','empty-later','occupied-other','occupied-eligible','occupied-match','occupied-match-eligible']
RES_BAD=['invalid-header0','invalid-header1','invalid-header2','invalid-header3','invalid-body0','invalid-body1','invalid-body2','overflow','duplicate','invalid-empty0','invalid-empty1','invalid-empty2']
PIN_OK=['empty-first','empty-later','live-nonrelease','live-release-other','live-release-match']
PIN_BAD=['empty-invalid-nonce','invalid-header0','invalid-header1','invalid-header2','invalid-backlink0','invalid-backlink1']
POST=['fail0.0','fail1.0','fail1.1','fail2.0','fail2.1','fail2.2','fail2.3','success']

def corr(name):
    s=[]; c=[]
    def scalars(prefix,labels):
        for x in labels:s.append(prefix+'.'+x)
    if name=='prelude':
        for call in ['arena.as_chunks','resident.as_chunks','pin.as_chunks','timestamp.as_chunks','candidate.split_at_mut']:
            scalars(call,['tuple.constructor.left.data->designated','tuple.constructor.left.len->designated','tuple.constructor.right.data->designated','tuple.constructor.right.len->designated'])
        for call in ['resident.first_chunk','pin.first_chunk','timestamp.first_chunk_mut']:
            s.append(call+'.Option.pointer.constructor->designated-return')
        for view in ['resident.word-range','pin.word-range','resident.nested-chunks-tail','pin.nested-chunks-tail']:
            scalars(view,['element-width8.source->scale.operand','element-unit-offset.source->scale.operand','scale.multiply.bytes'])
        scalars('candidate.array-to-slice',['array.data->coercion.source.data','fixed2048->coercion.source.len','coercion.data->received.slice.data','coercion.len->received.slice.len'])
        # A global bound for the three loop statement final unit/join pairs.
        for loop in ['resident','timestamp-tail','pin']:scalars(loop,['final-false.while-unit','final-false.statement-continuation'])
    if name.startswith('resident.'):
        scalars('resident',['body.scope-entry','header-if.unit','header-if.continuation','occupied-if.unit','occupied-if.continuation','body-shape-if.unit','body-shape-if.continuation','let-else.statement-continuation','requested-if.unit','requested-if.continuation','duplicate-if.unit','duplicate-if.continuation','eligibility-if.unit','eligibility-if.continuation'])
        if name.split('.',1)[1].startswith('occupied') or name in ['resident.overflow','resident.duplicate']:
            c.append(('checked_add.Option16.constructor->designated-return',16))
    if name.startswith('pin.'):
        scalars('pin',['body.scope-entry','entry-if.unit','entry-if.continuation','header-if.unit','header-if.continuation','backlink-if.unit','backlink-if.continuation','release-if.unit','release-if.continuation'])
    if name=='tail-body':
        s.append('timestamp-tail.body.scope-entry')
        c.append(('to_le_bytes.array8.constructor->designated-return',8))
    if name=='mask-store':c.append(('to_le_bytes.array8.constructor->designated-return',8))
    if name.startswith('post.'):
        for condition in ['duplicate-release','aggregate-pins','aggregate-state']:scalars(condition,['if.unit','if.continuation'])
    terminal=(name.startswith('post.fail') or (name.startswith('resident.') and name.split('.',1)[1] in RES_BAD) or (name.startswith('pin.') and name.split('.',1)[1] in PIN_BAD))
    if terminal:
        c.append(('reject.SemanticReply24.constructor->designated-return',24))
        c.append(('semantic.received-reject-reply24->semantic-designated-return24',24))
        scalars('return',['innermost-lexical-scope-exit','loop-or-conditional-scope-exit','outer-conditional-scope-exit'])
    return s,c

def total(items,counts):
    s=sum(counts[n][0]*r for n,r in items);c=sum(counts[n][1]*r for n,r in items)
    return {'scalars':s,'copies':c,'scalar_groups':(s+15)//16,'groups':(s+15)//16+c}
def norm(rec):return [(x['component'],x['repeat']) for x in rec['components']]

def recipes():
    # Independent domain reconstruction: all n,m completions; every resident
    # prefix terminal (pin configuration is not reached); every pin prefix for n.
    out={}
    for n in range(1,65):
        for m in range(1,65):
            out[f'complete.n{n}.m{m}']=[('prelude',1),('resident-test',n+1),('resident.occupied-match-eligible',n),('tail-test',65-n),('tail-body',64-n),('pin-init',1),('pin-test',m+1),('pin.live-release-match',m),('mask-store',1),('post.fail2.3',1)]
    for i in range(64):
        for bad in RES_BAD:
            out[f'resident-prefix{i}.{bad}']=[('prelude',1),('resident-test',i+1),('resident.occupied-match-eligible',i),('resident.'+bad,1)]
    for n in range(1,65):
        for i in range(64):
            for bad in PIN_BAD:
                out[f'pin.n{n}.prefix{i}.{bad}']=[('prelude',1),('resident-test',n+1),('resident.occupied-match-eligible',n),('tail-test',65-n),('tail-body',64-n),('pin-init',1),('pin-test',i+1),('pin.live-release-match',i),('pin.'+bad,1)]
    return out

def check_groups(groups):
    ids=[];s=c=0
    for g in groups:
        e=g['events'];need(bool(e),'empty group')
        if g['kind']=='scalar':need(len(e)<=16 and all(x['kind']=='scalar' and x['bytes']==0 for x in e),'scalar group') ;s+=len(e)
        else:
            need(g['kind']=='copy' and len(e)==1 and e[0]['kind']=='copy' and 0<e[0]['bytes']<=128,'copy group');c+=1
        ids.extend(x['id'] for x in e)
    need(len(ids)==len(set(ids)),'duplicate event id')
    return s,c

def pack(items,templates):
    events=[]
    for name,repeat in items:
        for i in range(repeat):
            for j,event in enumerate(templates[name]):events.append(dict(event,id=f'{name}/{i}/{j}'))
    scalars=[x for x in events if x['kind']=='scalar'];copies=[x for x in events if x['kind']=='copy']
    groups=[{'kind':'scalar','events':scalars[i:i+16]} for i in range(0,len(scalars),16)]
    groups.extend({'kind':'copy','events':[x]} for x in copies)
    return groups

# Independent old byte-offset logical model. It intentionally logs only required
# arena payload reads, not harmless immutable fixture/reference formation.
def old(rows,pins,n,m,kind,requested,release,prior,entry_limit=U):
    arena=b''.join(struct.pack('<8Q',*r) for r in rows)+b''.join(struct.pack('<6Q',*p) for p in pins)
    reads=[];scratch=bytearray([165]*648);count=total=rp=live=matches=0;found=empty=free=U;mask=0
    def rr(i,j):reads.append(('r',i,j));return struct.unpack_from('<Q',arena,i*64+j*8)[0]
    def pr(i,j):reads.append(('p',i,j));return struct.unpack_from('<Q',arena,4096+i*48+j*8)[0]
    def done(reason):return reason,(count,total,rp,live,matches,found,empty,free),bytes(scratch),reads
    for i in range(n):
        occupied,function,size,pinc=rr(i,0),rr(i,1),rr(i,2),rr(i,3)
        if occupied>1 or pinc>m or rr(i,6)!=0 or rr(i,7)!=0:return done(13)
        if occupied==1:
            rp+=pinc
            if function>=80000 or size==0 or size>entry_limit:return done(13)
            if total+size>U:return done(10)
            total+=size;count+=1
            if function==requested:
                if found!=U:return done(7)
                found=i
        elif function!=U or size!=0 or pinc!=0:return done(13)
        elif empty==U:empty=i
        timestamp=rr(i,4);scratch[i*8:i*8+8]=struct.pack('<Q',timestamp)
        if occupied==1 and pinc==0:mask|=1<<i
    for i in range(n,64):scratch[i*8:i*8+8]=b'\0'*8
    for i in range(m):
        target,nonce=pr(i,0),pr(i,1)
        if target==U:
            if nonce!=0:return done(13)
            if free==U:free=i
        else:
            if target>=n or nonce==0 or nonce>=prior[3] or rr(target,0)!=1 or rr(target,3)==0:return done(13)
            live+=1
            if kind==12 and nonce==release:matches+=1
    scratch[640:648]=struct.pack('<Q',mask)
    if matches>1:return done(11)
    if rp!=prior[2] or live!=prior[2]:return done(13)
    if count!=prior[0] or total!=prior[1] or prior[2]>m or prior[3]==0:return done(13)
    return done(0)

# Separate row-reference logical model, independently transcribed from new G2.
def new(rows,pinrows,n,m,kind,requested,release,prior,entry_limit=U):
    resident_words=[[int(x).to_bytes(8,'little') for x in row] for row in rows]
    pin_words=[[int(x).to_bytes(8,'little') for x in row] for row in pinrows]
    log=[];candidate=bytearray([165]*648);count=total=rp=live=matches=0;found=empty=free=U;eligibility=0
    def word(a,i,j,tag):log.append((tag,i,j));return int.from_bytes(a[i][j],'little')
    def result(code):return code,(count,total,rp,live,matches,found,empty,free),bytes(candidate),log
    slot=0
    while slot<n:
        occupied=word(resident_words,slot,0,'r');function=word(resident_words,slot,1,'r');size=word(resident_words,slot,2,'r');pinc=word(resident_words,slot,3,'r')
        if occupied>1 or pinc>m or word(resident_words,slot,6,'r')!=0 or word(resident_words,slot,7,'r')!=0:return result(13)
        if occupied==1:
            rp+=pinc
            if function>=80000 or size==0 or size>entry_limit:return result(13)
            summed=total+size
            if summed>U:return result(10)
            total=summed;count+=1
            if function==requested:
                if found!=U:return result(7)
                found=slot
        elif function!=U or size!=0 or pinc!=0:return result(13)
        elif empty==U:empty=slot
        log.append(('r',slot,4));candidate[slot*8:slot*8+8]=resident_words[slot][4]
        if occupied==1 and pinc==0:eligibility|=1<<slot
        slot+=1
    while slot<64:candidate[slot*8:slot*8+8]=(0).to_bytes(8,'little');slot+=1
    pin=0
    while pin<m:
        target=word(pin_words,pin,0,'p');nonce=word(pin_words,pin,1,'p')
        if target==U:
            if nonce!=0:return result(13)
            if free==U:free=pin
        else:
            if target>=n or nonce==0 or nonce>=prior[3]:return result(13)
            if word(resident_words,target,0,'r')!=1 or word(resident_words,target,3,'r')==0:return result(13)
            live+=1
            if kind==12 and nonce==release:matches+=1
        pin+=1
    candidate[640:648]=eligibility.to_bytes(8,'little')
    if matches>1:return result(11)
    if rp!=prior[2] or live!=prior[2]:return result(13)
    if count!=prior[0] or total!=prior[1] or prior[2]>m or prior[3]==0:return result(13)
    return result(0)

def semantic_cases():
    cases=[]
    def run(label,rows,pins,n,m,kind=1,requested=80000,release=0,prior=None,limit=U,expected=None):
        if prior is None:prior=(sum(r[0]==1 for r in rows[:n]),sum(r[2] for r in rows[:n] if r[0]==1),sum(r[3] for r in rows[:n] if r[0]==1),U)
        a=old(rows,pins,n,m,kind,requested,release,prior,limit);b=new(rows,pins,n,m,kind,requested,release,prior,limit)
        need(a==b,'semantic/read/partial scratch mismatch '+label)
        if expected is not None:need(a[0]==expected,'wrong first reason '+label)
        cases.append({'name':label,'reason':a[0],'reads':len(a[3]),'trace_sha256':sha(json.dumps(a[3]).encode()),'partial_candidate_sha256':sha(a[2])})
    empty=[[0,U,0,0,U,99,0,0] for _ in range(64)];free=[[U,0,91,92,93,94] for _ in range(64)]
    for n in range(1,65):
        for m in range(1,65):run(f'all-capacities.{n}.{m}',empty,free,n,m,expected=0)
    occupied=[[1,i,1,1,U if i%2 else i,99,0,0] for i in range(64)]
    tokens=[[i,i+1,11,12,13,14] for i in range(64)]
    for kind in range(1,14):run(f'kind.{kind}.MAX-timestamps',occupied,tokens,64,64,kind,release=64,prior=(64,64,64,65),expected=0)
    run('valid-full-witness',occupied,tokens,64,64,prior=(64,64,64,65),expected=0)
    # Every resident read/refusal edge, with a nonzero prefix to expose partial scratch.
    mutations=[(0,2,13),(3,65,13),(6,1,13),(7,1,13),(1,80000,13),(2,0,13),(2,2,13)]
    for j,value,reason in mutations:
        r=copy.deepcopy(occupied);r[3][j]=value
        run(f'resident-fault.{j}.{value}',r,tokens,64,64,prior=(64,64,64,65),limit=1,expected=reason)
    for j,value in [(1,1),(2,1),(3,1)]:
        r=copy.deepcopy(empty);r[4][j]=value;run(f'empty-shape.{j}',r,free,64,64,expected=13)
    r=copy.deepcopy(occupied);r[0][2]=U;r[1][2]=1;run('checked-total-overflow',r,tokens,64,64,prior=(64,64,64,65),expected=10)
    r=copy.deepcopy(occupied);r[1][1]=r[0][1];run('duplicate-requested',r,tokens,64,64,requested=0,prior=(64,64,64,65),expected=7)
    for label,pv in [('entry-range',[64,1]),('zero-nonce',[0,0]),('equal-next',[0,65]),('MAX-nonce',[0,U]),('empty-nonce',[U,1])]:
        pp=copy.deepcopy(tokens);pp[3][:2]=pv;run(label,occupied,pp,64,64,prior=(64,64,64,65),expected=13)
    pp=copy.deepcopy(tokens);pp[3][1]=pp[2][1];run('duplicate-release',occupied,pp,64,64,kind=12,release=3,prior=(64,64,64,65),expected=11)
    for k,prior in enumerate([(63,64,64,65),(64,63,64,65),(64,64,63,65),(64,64,65,65),(64,64,64,0)]):run('post.'+str(k),occupied,tokens,64,64,prior=prior,expected=13)
    r=copy.deepcopy(empty);r[0]=[1,10,1,1,0,0,0,0]
    run('post.live-count-after-equal-resident-pins',r,free,2,2,prior=(1,1,1,2),expected=13)
    run('post.zero-next-after-empty-scans',empty,free,2,2,prior=(0,0,0,0),expected=13)
    sealed_witness=read('g2-witness.json')
    wr=[[r[k] for k in ['occupied','function','bytes','pins','last_used','generation','reserved6','reserved7']] for r in sealed_witness['residents']]
    wp=[[p['entry'],p['nonce'],0,0,0,0] for p in sealed_witness['pins']]
    ws=sealed_witness['state'];wf=sealed_witness['fixture'];record=sealed_witness['record']
    need([r['slot'] for r in sealed_witness['residents']]==list(range(64)) and [p['pin'] for p in sealed_witness['pins']]==list(range(64)),'witness ordering')
    run('exact-sealed-producer-witness',wr,wp,wf['slots'],wf['pins'],kind=record['kind'],requested=record['requested_function'],prior=(ws['resident_count'],ws['resident_bytes'],ws['pin_count'],ws['next_nonce']),limit=wf['entry'],expected=0)
    # Distinct bad backlink0/backlink3 require an empty resident row that itself
    # passes validation, and a token pointing at it.
    r=copy.deepcopy(empty);pp=copy.deepcopy(free);pp[0]=[0,1,0,0,0,0];run('bad-backlink-occupied',r,pp,1,1,prior=(0,0,0,2),expected=13)
    r=copy.deepcopy(occupied);r[0][3]=0;run('bad-backlink-pins',r,tokens,64,64,prior=(64,64,63,65),expected=13)
    for next_nonce in [U-1,U]:run('nonce-boundary.'+str(next_nonce),occupied,tokens,64,64,prior=(64,64,64,next_nonce),expected=0)
    rng=random.Random(0xC3A43397)
    for k in range(256):
        r=copy.deepcopy(occupied);pp=copy.deepcopy(tokens)
        if k%2:r[rng.randrange(64)][rng.choice([0,1,2,3,4,5,6,7])]=rng.choice([0,1,2,64,65,79999,80000,U])
        else:pp[rng.randrange(64)][rng.choice([0,1,2,3,4,5])]=rng.choice([0,1,63,64,65,U])
        run('deterministic-mutant.'+str(k),r,pp,64,64,kind=1+k%13,release=3,prior=(64,64,64,65))
    # Six manually constructed valid states: empty, publish, pin, release,
    # timestamp update, eviction. This is G2 relation coverage, not full transitions.
    r=copy.deepcopy(empty);pp=copy.deepcopy(free)
    run('sequence.empty',r,pp,2,2,expected=0)
    r[0]=[1,10,2,0,U,1,0,0];run('sequence.publish',r,pp,2,2,expected=0)
    r[0][3]=1;pp[0]=[0,1,0,0,0,0];run('sequence.pin',r,pp,2,2,prior=(1,2,1,2),expected=0)
    r[0][3]=0;pp[0]=[U,0,0,0,0,0];run('sequence.release',r,pp,2,2,prior=(1,2,0,2),expected=0)
    r[0][4]=U-1;run('sequence.touch',r,pp,2,2,prior=(1,2,0,2),expected=0)
    r[0]=[0,U,0,0,0,2,0,0];run('sequence.evict',r,pp,2,2,prior=(0,0,0,2),expected=0)
    identity_values=[0,1,255,256,U,U-1]+[1<<i for i in range(64)]+[U^(1<<i) for i in range(64)]+[rng.getrandbits(64) for _ in range(252)]
    need(len(identity_values)==386,'identity count')
    for value in identity_values:
        b=value.to_bytes(8,'little');need(int.from_bytes(b,'little').to_bytes(8,'little')==b,'LE identity')
    return cases,len(identity_values)

def main():
    seal=read('seal.json');need(sha((P/'seal.json').read_bytes())==SEAL,'producer seal mismatch')
    need((seal['member_count'],seal['member_bytes'])==(29,2106607),'producer member totals')
    for member in seal['members']:
        b=(ROOT/member['path']).read_bytes();need(len(b)==member['bytes'] and sha(b)==member['sha256'],'producer custody '+member['path'])
    src=(P/'source/cache_state.rs.txt').read_text();need(sha(src.encode())==SOURCE,'source identity')
    g2=(P/'g2.rs.txt').read_text();need(src.count(g2)==1,'G2 text not exact unique source excerpt')
    pos=src.index(g2);assembly=read('source-assembly.json')
    need(sha(src[:pos].encode())==assembly['prefix_sha256'],'unchanged-prefix anchor')
    need(sha(src[pos+len(g2):].encode())==assembly['suffix_sha256'],'unchanged-suffix anchor')
    need('const SEMANTIC_RECORD: u64 = 7680;' in src,'semantic record cap changed')
    need('b.len() != ARENA_BYTES || steps.spent != 0' in src,'arena guard absent')
    need(all(x in g2 for x in ['&[[[u8; 8]; 8]; 64]','&[[[u8; 8]; 6]; 64]','timestamp_words[slot] = *last_used_le;','index_bytes[128..136]','nonce >= *next_nonce','entry >= configured_slots']),'source anchor')
    components=read('components.json');templates=components['templates'];need(set(templates)==set(EXPECTED),'component domain')
    corrected={};expanded={};addendum={}
    for name,ev in templates.items():
        raw=(sum(e['kind']=='scalar' for e in ev),sum(e['kind']=='copy' for e in ev))
        need(raw==EXPECTED[name],'component hand equation '+name)
        need(all(e['kind'] in ['copy','scalar'] and ((e['kind']=='scalar' and e['bytes']==0) or (e['kind']=='copy' and 0<e['bytes']<=128)) for e in ev),'bad primitive event')
        s,c=corr(name);corrected[name]=(raw[0]+len(s),raw[1]+len(c))
        addendum[name]={'scalar_edges':s,'distinct_copies':[{'operation':a,'bytes':b} for a,b in c]}
        expanded[name]=copy.deepcopy(ev)+[{'kind':'scalar','bytes':0,'operation':'independent.'+a} for a in s]+[{'kind':'copy','bytes':b,'operation':'independent.'+a} for a,b in c]
    # Checked weighted domination makes incompatible per-row relaxations safe.
    weight=lambda n:corrected[n][0]+16*corrected[n][1]
    need(all(weight('resident.'+n)<=weight('resident.occupied-match-eligible') for n in RES_OK),'resident dominator')
    need(all(weight('pin.'+n)<=weight('pin.live-release-match') for n in PIN_OK),'pin dominator')
    need(all(weight('post.'+n)<=weight('post.fail2.3') for n in POST),'post dominator')
    fresh=recipes();need(len(fresh)==29440,'independent recipe domain')
    supplied=zipped('recipes.json.gz')['recipes'];need(len(supplied)==29440,'producer recipe count')
    # Compare the complete multisets without depending on producer labels.
    signature=lambda rows:tuple((a,b) for a,b in rows if b)
    need(sorted(signature(x) for x in fresh.values())==sorted(signature(norm(x)) for x in supplied),'recipe completeness mismatch')
    for r in supplied:need(total(norm(r),EXPECTED)=={k:r[k] for k in ['scalars','copies','scalar_groups','groups']},'producer recipe arithmetic')
    maxima=max(((total(v,corrected)['groups'],k,v) for k,v in fresh.items()),key=lambda x:x[0]);upper=total(maxima[2],corrected)
    need(upper['groups']<=2560,'G2 cap exceeded')
    witness=read('g2-witness.json');wi=norm(witness);wtotal=total(wi,corrected)
    need(total(wi,EXPECTED)=={k:witness[k] for k in ['scalars','copies','scalar_groups','groups']},'witness arithmetic')
    original=zipped('complete-upper-ledger.json.gz');need(check_groups(original['groups'])==(24965,771),'original ledger shape')
    groups=pack(maxima[2],expanded);need(check_groups(groups)==(upper['scalars'],upper['copies']),'corrected ledger shape')
    write('correction-addendum.json',{'schema':1,'source_sha256':SOURCE,'interpretation':'complete conservative source-control/return-edge overbound; incompatible conditional continuations may dominate terminals','components':addendum,'corrected_counts':{k:{'scalars':s,'copies':c} for k,(s,c) in corrected.items()}})
    (OUT/'corrected-upper-ledger.json.gz').write_bytes(gzip.compress(json.dumps({'schema':1,'path':maxima[1],'groups':groups},sort_keys=True,separators=(',',':')).encode(),mtime=0))
    # Logical capacity inventory: keep every submitted owner and add actual
    # array-to-slice coercion and array-pattern temporary phases explicitly.
    life=read('G2-lifetimes.json');phases=[]
    for phase in life['phases']:
        places=copy.deepcopy(phase['places'])
        if any(k.startswith('reject_reply.') for k in places):
            places['independent.semantic.complete_reply_designated_return']=24
        if phase['id']=='view.as_chunks':
            places.update({'independent.array_to_slice.source_view':16,'independent.array_to_slice.received_view':16,
                           'independent.Region.start_constant_source':24,'independent.Region.end_constant_source':24})
        phases.append({'id':phase['id'],'Control':sum(places.values()),'Wire':24,'Setup':80,'places':places})
    # Pattern projection is ephemeral in the resident/pin body. All named field
    # refs and scalar locals are retained through the entire lexical body.
    for base_id,new_id in [('resident.row_index','resident.array_pattern'),('pin.backlink_index','pin.backlink_array_pattern')]:
        base=next(p for p in phases if p['id']==base_id);places=copy.deepcopy(base['places'])
        places.update({'independent.pattern.received_row_pointer':8,'independent.pattern.field_projection_operand':8,'independent.pattern.projected_reference_source':8})
        phases.append({'id':new_id,'Control':sum(places.values()),'Wire':24,'Setup':80,'places':places})
    base=next(p for p in phases if p['id']=='view.first_chunk_expect')
    places={k:v for k,v in base['places'].items() if k.startswith(('base.','block.'))}
    places.update({'independent.pattern.received_row_pointer':8,'independent.pattern.field_projection_operand':8,'independent.pattern.projected_reference_source':8})
    phases.append({'id':'record-and-prior.array_patterns','Control':sum(places.values()),'Wire':24,'Setup':80,'places':places})
    places={k:v for k,v in base['places'].items() if k.startswith(('base.','block.'))}
    places.update({'tail.Index.receiver_source':8,'tail.Index.receiver_received':8,'tail.Index.index_source':8,'tail.Index.index_received':8,
                   'tail.Index.bound_operands_and_bool':17,'tail.Index.scale_operands_and_result':24,'tail.Index.address_operands_and_result':24,
                   'tail.Index.return_source':8,'tail.Index.return_received':8,'tail.to_LE.self_source':8,'tail.to_LE.self_received':8,
                   'tail.to_LE.array_constructor':8,'tail.to_LE.array_designated_return':8,'tail.to_LE.complete_array_received':8,
                   'tail.assignment.unit_and_continuation':2,'tail.loop.implicit_unit':1})
    phases.append({'id':'timestamp-tail.index-and-array-return','Control':sum(places.values()),'Wire':24,'Setup':80,'places':places})
    peak=max(p['Control'] for p in phases);need(peak<=1280,'Control cap');need(max(p['Wire'] for p in phases)<=256,'Wire cap');need(max(p['Setup'] for p in phases)<=256,'Setup cap')
    need(all('block.row' in p['places'] for p in phases if p['id'].startswith(('resident.','pin.'))),'row lexical owner omitted')
    write('G2-lifetimes.json',{'schema':1,'scope':'named logical G2 only; no whole role union or compiler stack claim','caller_Control_base':480,'block_named_Control':232,'Control_peak':peak,'Control_allowance':1280,'Wire_peak':24,'Wire_allowance':256,'Setup_peak':80,'Setup_allowance':256,'phases':phases,'source_payload_new_bytes':0})
    # Mutation controls are deliberately failing in-memory checks; none mutates inputs.
    mutations=[]
    def rejected(label,fn):
        try:fn()
        except ValueError as e:mutations.append({'name':label,'rejected':True,'reason':str(e)});return
        raise ValueError('mutation accepted '+label)
    rejected('producer-seal-byte',lambda:need(sha((P/'seal.json').read_bytes()+b' ')==SEAL,'seal digest'))
    rejected('17-scalars-in-group',lambda:check_groups([{'kind':'scalar','events':[{'id':str(i),'kind':'scalar','bytes':0} for i in range(17)]}]))
    rejected('129-byte-copy',lambda:check_groups([{'kind':'copy','events':[{'id':'x','kind':'copy','bytes':129}]}]))
    rejected('duplicate-event-id',lambda:check_groups([{'kind':'scalar','events':[{'id':'x','kind':'scalar','bytes':0},{'id':'x','kind':'scalar','bytes':0}]}]))
    mutant_addendum=copy.deepcopy(addendum)
    mutant_addendum['resident.occupied-match-eligible']['distinct_copies']=[]
    rejected('missing-Option16-return-copy',lambda:need(any(c['bytes']==16 and 'checked_add' in c['operation'] for c in mutant_addendum['resident.occupied-match-eligible']['distinct_copies']),'required Option16 return copy missing'))
    mutant_recipes=copy.deepcopy(fresh);del mutant_recipes['complete.n64.m64']
    rejected('missing-recipe',lambda:need(len(mutant_recipes)==29440,'recipe domain incomplete'))
    rejected('missing-row-owner',lambda:need('block.row' in {k:v for k,v in phases[2]['places'].items() if k!='block.row'},'row owner missing'))
    rejected('source-byte-change',lambda:need(sha(src.replace('pins == 0','pins != 0',1).encode())==SOURCE,'source mutation'))
    cases,identity=semantic_cases();write('finite-cases.json',{'schema':1,'case_count':len(cases),'cases':cases,'LE_identity_samples':identity,'authority':'independent finite offline logical relations only; neither Rust nor full semantic transitions executed'})
    result={'schema':1,'producer_seal_sha256':SEAL,'source_sha256':SOURCE,'producer_exact_totals_accepted':False,'corrected_complete_G2_upper':upper,'corrected_maximum_path':maxima[1],'corrected_valid_witness':wtotal,'recipe_count':len(fresh),'primitive_component_count':len(EXPECTED),'finite_logical_cases':len(cases),'LE_identity_samples':identity,'Control_peak':peak,'Wire_peak':24,'Setup_peak':80,'mutation_controls':mutations,'G2_source_semantics_scoped_review':'preserved under admitted source bounds; root must select correction addendum','whole_implementation_G3_G4_G5_lifetime_native_GA_accepted':False,'producer_code_imported_or_executed':False}
    write('check-result.json',result);print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
