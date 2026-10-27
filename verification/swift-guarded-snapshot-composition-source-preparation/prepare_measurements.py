"""Generate only private sizeof/align measurement definitions from released types."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parent
ADDENDUM=ROOT.parent/'swift-guarded-snapshot-encoder-independent/candidate-review/source-place-addendum.json'
assert hashlib.sha256(ADDENDUM.read_bytes()).hexdigest()=='c63de76852dc11819935856021ad325208946dd8008e0910dd508a70b9460ce8'
rows=json.loads(ADDENDUM.read_text())['all_fresh_helper_rows']
groups={'encoder':[],'loader':[]}
for row in rows:groups['loader' if 'FileIdentityV1' in row['name'] else 'encoder'].append(row)
for name,group in groups.items():
    symbol='MIXER_COMPOSITION_'+name.upper()+'_HELPER_LAYOUTS_V1'
    lines=['// Root-released append-only private measurement seam. No behavior calls.',
           '#[cfg(mixer_snapshot_composition_layout)]','#[used]',f'static {symbol}:[usize;{len(group)*2}]=[']
    for row in group:
        ty=row['name']
        lines.append(f' std::mem::size_of::<{ty}>(),std::mem::align_of::<{ty}>(), // {ty}')
    lines+= ['];']
    (ROOT/'implementation'/(name+'_measurement.rs')).write_text('\n'.join(lines)+'\n')

# Inferred argument types are written explicitly where context was originally
# supplied by map_err/is_some_and. Bodies and captured names are unchanged.
captures=[]
def add(name,line,expr,multiplicity=1,context='encoder'):
    captures.append({'name':name,'frozen_line':line,'expression':expr,'multiplicity':multiplicity,'context':context})
add('word-conversion',792,'|_:std::num::TryFromIntError| SnapshotEncodeErrorV2::Arithmetic')
add('span-end',835,'|end:usize| end <= self.source',context='span-method')
add('provenance-map-error',936,'|_:()| SnapshotEncodeErrorV2::Arithmetic')
add('memory-absent',986,'|| field(2, 0, 0)')
add('table-absent',987,'|| field(3, 0, 0)')
add('runtime-map-error',1015,'|_:()| SnapshotEncodeErrorV2::Arithmetic')
add('function-total',1035,'|n:usize| n <= 80000')
for member in ['signatures','parameters','imports','functions','globals','exports','data','elements']:
    add('entry-'+member,1169,'|| field(16, sid, index)',context='entry!('+member+')')
add('parameter-range',1178,'|n:usize| n <= m.parameters.len()',context='view-method')
add('record-word-result',1257,'|| field(21, sid, index)')
add('directory-absent',1341,'|| field(28, 0, 0)')
for name,line in [('source-copy-count',1347),('source-offset',1349),('metadata-index',1357)]:
    add(name,line,'|_:std::num::TryFromIntError| SnapshotEncodeErrorV2::Arithmetic')
add('runtime-convert',255,'|n:usize| u64::try_from(n).map_err(|_|())',context='runtime-bridge')
add('runtime-inner-convert',255,'|_:std::num::TryFromIntError| ()',context='runtime-bridge')
for name,line in [('provenance-source-convert',1392),('provenance-metadata-convert',1393),('provenance-scratch-convert',1393)]:
    add(name,line,'|_:std::num::TryFromIntError| ()',context='provenance-bridge')

static_captures=[x for x in captures if x['context']!='view-method']
lines=['\n// Exact-expression closure shape definitions; never evaluate the closures.',
       '#[cfg(mixer_snapshot_composition_layout)]',
       'impl SpanCheckV2 {',
       ' const fn composer_measure_span_capture_v1(&self)->(usize,usize){',
       '  let c=|end:usize| end <= self.source;',
       '  (std::mem::size_of_val(&c),std::mem::align_of_val(&c))',
       ' }','}',
       '#[cfg(mixer_snapshot_composition_layout)]',
       'const fn composer_measure_parameter_span_capture_v1(view:&SnapshotViewV2<\'_>)->(usize,usize){',
       '  let m=&view.proof.metadata;',
       '  let c=|n:usize| n <= m.parameters.len();',
       '  (std::mem::size_of_val(&c),std::mem::align_of_val(&c))',
       ' }',
       '#[cfg(mixer_snapshot_composition_layout)]','#[used]',
       'static COMPOSITION_PARAMETER_CAPTURE_MEASURER_V1:fn(&SnapshotViewV2<\'_>)->(usize,usize)=composer_measure_parameter_span_capture_v1;',
       '#[cfg(mixer_snapshot_composition_layout)]','#[used]',f'static MIXER_COMPOSITION_ENCODER_CAPTURE_LAYOUTS_V1:[usize;{len(static_captures)*2}]=[']
for entry in static_captures:
    if entry['context']=='span-method':
        pair='SpanCheckV2 {source:0,section:0,index:0}.composer_measure_span_capture_v1()'
    else:
        locals='let sid=0usize;let index=0usize;' if 'sid' in entry['expression'] else ''
        pair='{'+locals+'let c='+entry['expression']+';(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}'
    lines += [f' {pair}.0,{pair}.1, // {entry["name"]}']
lines+= ['];']
lines+= [
 '#[cfg(mixer_snapshot_composition_layout)]',
 'const fn composer_checked_capture_static_sum_v1()->Option<usize>{',
 ' let mut i=0usize;let mut sum=0usize;',
 ' while i<MIXER_COMPOSITION_ENCODER_CAPTURE_LAYOUTS_V1.len(){',
 '  sum=match sum.checked_add(MIXER_COMPOSITION_ENCODER_CAPTURE_LAYOUTS_V1[i]){Some(n)=>n,None=>return None};',
 '  i+=2;',
 ' }Some(sum)',
 '}',
 '#[cfg(mixer_snapshot_composition_layout)]','#[used]',
 'static MIXER_COMPOSITION_CAPTURE_PARTIAL_SUM_V1:[usize;2]=match composer_checked_capture_static_sum_v1(){Some(n)=>[1,n],None=>[0,0]};',
 '// This checked sum covers only the25 statically evaluable exact occurrences.',
 '// The separately compiler-measured parameter-range capture still joins the',
 '// occurrence roster; neither number is a source/phase/foundation floor.'
]
with (ROOT/'implementation/encoder_measurement.rs').open('a') as f:f.write('\n'.join(lines)+'\n')
(ROOT/'encoder-helper-ledger.json').write_text(json.dumps({
    'schema':1,'release_sha256':'6f241f56431eec5f1d192fc97df51adcaea960c9feea211c214b053a202f7ebb',
    'addendum_sha256':hashlib.sha256(ADDENDUM.read_bytes()).hexdigest(),
    'groups':groups,'captures':captures,'static_capture_names':[x['name'] for x in static_captures],
    'parameter_capture':'Exact method context measured in compiler IR through a private used function pointer; no fake proof or invalid reference is constructed.',
    'multiplicity_scope':'One named source occurrence per listed expression; entry macro expands into eight distinct source occurrences. At most one entry branch is live per record_word call. Loop iterations reuse those same source places; operation counts are separately audited.',
    'overlap':'Existing52/27/58 shapes are identities, not extra live copies. The exact capture/return/Option/pattern occurrence inventory must be reconciled with existing EncoderInit/Block/Caller and new composition caller aggregates. No aggregate total or floor is selected.',
    'behavior':'All original encoder/bridge behavior bodies byte-identical; only private const/static measurement definitions appended.'
},indent=2)+'\n')
print(json.dumps({'helper_shapes':len(rows),'encoder_shapes':len(groups['encoder']),'loader_shapes':len(groups['loader']),'exact_capture_occurrences':len(captures),'static_captures':len(static_captures)}))
