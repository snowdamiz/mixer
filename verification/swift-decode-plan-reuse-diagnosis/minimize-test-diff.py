from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent
p=H/'source/src/experimental_swift_reactor/cache_tests.rs'
s=p.read_text();marker='\n#[test]\nfn plan_reuse_observation()'
i=s.index(marker)
original=(H.parents[1]/'vm/src/experimental_swift_reactor/cache_tests.rs').read_text()
p.write_text(original+s[i:])
# Keep appended common fixture bytes identical in both lanes.
b=H/'baseline/src/experimental_swift_reactor/cache_tests.rs';bs=b.read_text()
start=s.index('fn plan_reuse_wide_fixture(')
end=s.index('\n#[test]\nfn plan_reuse_header_lifetime',start) if '\n#[test]\nfn plan_reuse_header_lifetime' in s[start:] else len(s)
# Source order: common observation, prototype controls, wide builder, extra tests.
wide=s[start:end]
bi=bs.index('fn plan_reuse_wide_fixture(')
b.write_text(bs[:bi]+wide)
# The observation itself is taken from candidate's formatted common block.
s=p.read_text();start=s.index(marker);end=s.index('\nuse super::cache::plan_inspection',start)
bi=b.read_text().index(marker);be=b.read_text().index('fn plan_reuse_wide_fixture(')
b.write_text(original+s[start:end]+'\n'+wide)
print('preserved exact inherited test prefix and identical observation/wide fixtures')
