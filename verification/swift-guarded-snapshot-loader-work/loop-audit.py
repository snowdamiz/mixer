"""Source-bound manual backedge audit; no product import or execution."""
import json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent; R=D.parents[1]
B=R/'verification/swift-guarded-snapshot-funding-implementation/source/vm'
rows=[]
def row(path,line,kind,proof,limit):
 text=(B/path).read_text();lines=text.splitlines()
 rows.append(dict(path=str((B/path).relative_to(R)),line=line,source_line=lines[line-1],kind=kind,proof=proof,iteration_ceiling=limit))
A='src/experimental/account.rs';S='src/experimental/swift.rs';M='src/experimental/metadata.rs';V='src/experimental/validate.rs';E='src/experimental/reader.rs'
row(A,285,'positive-credit','Buffer.reserve copy iteration calls meter.work(1) before next.push; first failed attempt terminal','B+1')
row(S,451,'positive-credit','Source copy chunk calls meter.work(chunk.len()); input.chunks(16384) yields strictly positive nonempty chunks before extend; failed attempt terminal','B+1')
row(S,516,'positive-credit','ABI iteration charges module bytes+name bytes+signature count+34, hence >=34 before resolve; first attempt may execute prefix','B+1')
row(S,564,'fixed-outer','Three literal exports; exact m.exports.len()==3 is checked before entry. Each outer body has inner three attempts with positive export.name.bytes+1. Empty no-credit repetitions impossible here','3')
row(S,575,'positive-credit','Each export scan charges export.name.bytes+1 >=1 before compare','B+1')
row(S,608,'fixed-outer','Two literal segment categories, including empty categories; charge two setup/exit bodies without relying on credit','2')
row(S,612,'positive-credit','Segment iteration meter.work(1) before checked extent comparison','B+1')
for line,proof in [(60,'Reader.uint body begins Reader.byte, which charges1; maximum5 also explicit'),(79,'Reader.signed body begins Reader.byte; bits32/64 yields maximum5/10')]:row(E,line,'positive-credit',proof,'B+1')
for line,proof in [(154,'UTF8 lead iteration charges1 before accessing lead'),(168,'UTF8 continuation charges1 before byte access; width<=4'),(271,'Metadata section begins Reader.byte charge1'),(293,'Type iteration Reader.byte charge1'),(319,'Parameter iteration Reader.ty -> Reader.byte charge1'),(342,'Import iteration name -> Reader.count -> Reader.uint -> Reader.byte charge1'),(363,'Function iteration Reader.uint -> Reader.byte charge1'),(398,'Global iteration Reader.ty -> Reader.byte charge1'),(431,'Export iteration name -> Reader.count -> Reader.byte charge1'),(443,'Element segment iteration Reader.uint -> Reader.byte charge1'),(466,'Element payload iteration Reader.uint -> Reader.byte charge1'),(495,'Code-body iteration Reader.uint -> Reader.byte charge1'),(506,'Data segment iteration Reader.uint -> Reader.byte charge1'),(539,'Import audit meter.work(18) before audit'),(558,'Function audit meter.work(1)'),(564,'Export audit meter.work(1)'),(596,'Name comparison loop meter.work(1) before compare'),(615,'Sift loop meter.work(1) before child calculation'),(661,'Indices push charges1 before reserve/store'),(664,'Sift begins positive meter.work(1); caller prefix before attempt included'),(667,'Heapsort outer meter.work(1) before swap/sift'),(672,'compare_names charges1 before each pair comparison or final length comparison, even empty names')]:row(M,line,'positive-credit',proof,'B+1')
for line,proof in [(133,'call params pop -> pop_any charges1; empty parameter sequence has no loopbody'),(154,'Each function body reaches Reader.count -> Reader.byte charge1 before possible repeat; precharge state setup body included in each epoch'),(167,'Parameter locals Buffer.push charges1 before store'),(170,'Local group Reader.count -> Reader.byte charges1'),(178,'Each local Buffer.push charges1'),(195,'Instruction loop Reader.byte charges1 before opcode branch'),(320,'Branch-table label Reader.uint -> Reader.byte charges1'),(491,'Numeric pop -> pop_any charges1; numeric_type also caps count<=2'),(511,'Literal three pop iterations each pop_any charges1')]:row(V,line,'positive-credit',proof,'B+1')
# Source itself checked against these exact line identities. This rejects missing
# loop rows; classification/proof truth still needs independent semantic review.
for p in (A,S,M,V,E):
 text=(B/p).read_text().splitlines()
 maxline=630 if p==S else len(text)
 expected=[i for i,s in enumerate(text[:maxline],1) if s.lstrip().startswith(('for ','while ','loop {'))]
 got=[x['line'] for x in rows if x['path']==str((B/p).relative_to(R))]
 if sorted(got)!=expected:raise AssertionError((p,expected,got))
(D/'loop-audit.json').write_text(json.dumps(dict(schema=1,rows=rows,
 theorem='Each particular fully expanded acyclic source occurrence executes at most B+1 times if every enclosing dynamic backedge crosses a positive credit before repeat; fixed no-credit loops expanded separately. Nested loops do not multiply B: all successful positive charges share the same monotone meter. The final failed attempt contributes one additional epoch.',
 proof_status='manual-control-flow-argument; does not establish source-operation-to-host-action counting representation'),sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(loop_rows=len(rows),status='source-loop-roster-complete')))
