"""Closed type algebra over accepted declarations; no Rust code is executed.

This does not generalize to arbitrary Rust. Exact source hashes and the complete
existing twenty-row differential are mandatory in derive.py.
"""
import collections,re

def split(text,sep=','):
    stack=[];out=[];begin=0;pairs={'<':'>','[':']','(':')'}
    for i,c in enumerate(text):
        if c in pairs:stack.append(pairs[c])
        elif c in '>])':
            if not stack or stack.pop()!=c:raise ValueError('bad-type-bracket')
        elif c==sep and not stack:out.append(text[begin:i].strip());begin=i+1
    if stack:raise ValueError('unfinished-type')
    out.append(text[begin:].strip());return [s for s in out if s]

def normalize(t):
    t=t.strip()
    t={'AError':'SnapshotAdmissionErrorV1','Stop':'SnapshotStopV1','SwiftMetadata':'Metadata<SwiftDeclaration>'}.get(t,t)
    return re.sub(r'\b(?:[a-zA-Z_]\w*::)+', '', t)

class Graph:
    def __init__(self,decls):self.decls={d['name']:d for d in decls};self.active=set()
    def walk(self,t):
        t=normalize(t)
        if t in self.active:raise ValueError('recursive-owned-type:'+t)
        self.active.add(t)
        try:
            if t.startswith(('&','*const ','*mut ')):return {'nodes':1,'resources':{}}
            if t in ('()','!','u8','u16','u32','u64','u128','usize','i8','i16','i32','i64','i128','isize','bool','char','f32','f64','Duration','Instant'):
                return {'nodes':1,'resources':{}}
            if t.startswith('['):
                item,count=split(t[1:-1],';');v=self.walk(item);n=int(count.replace('_',''))
                if not 0<=n<=8192:raise ValueError('array-bound')
                return {'nodes':1+n*v['nodes'],'resources':{k:n*c for k,c in v['resources'].items()}}
            if t.startswith('('):return self.seq(split(t[1:-1]))
            head=t.split('<',1)[0];args=split(t[len(head)+1:-1]) if '<' in t else []
            if head in ('Vec','Box','Arc','File','Error'):
                if len(args)!=(0 if head in ('File','Error') else 1):raise ValueError('resource-arity')
                return {'nodes':1,'resources':{t.replace(' ',''):1}}
            if head=='Option':
                if len(args)!=1:raise ValueError('option-arity')
                return self.variant([[],args])
            if head=='Result':
                if len(args)!=2:raise ValueError('result-arity')
                return self.variant([[x] for x in args])
            d=self.decls[head]
            def fields(xs):
                for f in xs:
                    if head=='Metadata':
                        if args!=['SwiftDeclaration']:raise ValueError('metadata-specialization')
                        f=re.sub(r'\bD\b','SwiftDeclaration',f)
                    elif head=='Buffer':
                        if len(args)!=1:raise ValueError('buffer-specialization')
                        f=re.sub(r'\bT\b',args[0],f)
                    yield f
            if d['kind']=='struct':return self.seq(list(fields(d['fields'])))
            return self.variant([list(fields(v['fields'])) for v in d['variants']])
        finally:self.active.remove(t)
    def seq(self,fields):
        parts=[self.walk(t) for t in fields];r=collections.Counter()
        for p in parts:r.update(p['resources'])
        return {'nodes':1+sum(p['nodes'] for p in parts),'resources':dict(r)}
    def variant(self,variants):
        parts=[self.seq(v) for v in variants];r={}
        for p in parts:
            for k,c in p['resources'].items():r[k]=max(r.get(k,0),c)
        return {'nodes':1+max([0]+[p['nodes'] for p in parts]),'resources':r}

def extra_declarations():
    def struct(name,fields):return {'name':name,'kind':'struct','fields':fields}
    return [
        struct('Partial',['Option<AdoptedProof>','Vec<SwiftSlot>','Vec<PinRecord>','Vec<decode::Patch>','Vec<u8>','Vec<Option<ScanPlan>>','[Option<ReservationTicket>; 3]','Option<ReservationTicket>']),
        struct('SnapshotShapeV1',['[u64;9]','u64','u64','u64','u64']),
        struct('SnapshotPlanV1',['SnapshotShapeV1','u64','u64']),
        struct('SnapshotPhaseStorageV1',['Option<SnapshotPlanV1>','Option<[u8;4096]>','Option<AError>']),
    ]
