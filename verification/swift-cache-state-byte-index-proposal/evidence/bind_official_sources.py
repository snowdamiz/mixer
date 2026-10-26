"""Fetch/hash immutable official platform text only; execute none of it."""
from pathlib import Path
import hashlib,json,sys,urllib.request
root=Path(__file__).resolve().parents[1]
base="https://raw.githubusercontent.com/rust-lang/rust/b940084d7eb6a299eb4bfeb8e34901bc051e7ac4/library/core/src/"
sources={
 "slice/mod.rs":("8026ddec62fb732d01dc6fcb700fbf109aa5dd94d2391387db3202f405669d43",["fn as_chunks<","fn as_chunks_mut<","fn as_chunks_unchecked<","fn as_chunks_unchecked_mut<","fn split_at(&","fn split_at_mut(&","fn split_at_checked(&","fn split_at_mut_checked(&","fn split_at_unchecked(&","fn split_at_mut_unchecked(&"]),
 "slice/raw.rs":("0914968067f7e2bc798680c1edd72bcb032a9fd44ebb2b6fbc082a3a2b16941f",["fn from_raw_parts<","fn from_raw_parts_mut<"]),
 "ub_checks.rs":("d05a661966104ee074957fb06263b40efa586b56c80248b5ae74cfbf47ad5c70",["fn maybe_is_aligned_and_not_null(","fn maybe_is_aligned(","fn is_valid_allocation_size(","macro_rules! assert_unsafe_precondition"]),
 "num/uint_macros.rs":("39968a5edee5ecbe8bf38d38a87b6794e351076087c95483e1da083c8da0a19c",["fn checked_add(","fn checked_sub("])
}
rows=[]
for path,(expected,names) in sources.items():
 url=base+path;data=urllib.request.urlopen(url).read()
 actual=hashlib.sha256(data).hexdigest();assert actual==expected,(path,actual)
 lines=data.decode().splitlines();spans=[]
 for name in names:
  hits=[i+1 for i,line in enumerate(lines) if name in line]
  assert len(hits)==1,(name,hits)
  spans.append(dict(symbol=name,line=hits[0]))
 rows.append(dict(url=url,bytes=len(data),sha256=actual,symbols=spans))
result=dict(python=sys.version,command="python3 -B evidence/bind_official_sources.py",compiler_commit="b940084d7eb6a299eb4bfeb8e34901bc051e7ac4",sources=rows,
 fetch_text_only=True,compiler_or_platform_source_execution=False,
 intrinsic_grammar_boundary="Metadata, casts, raw-pointer arithmetic/metadata construction, exact/unchecked arithmetic, fixed-width LE conversion, bounded payload movement; see primitive-grammar.md",
 source_accounting_accepted=False)
(root/"official-source-bindings.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2,sort_keys=True))
