from pathlib import Path
H=Path(__file__).resolve().parent
for lane in ('baseline','source'):
 p=H/lane/'src/experimental_swift_reactor/cache_tests.rs'
 s=p.read_text();s+=(H/'common-tests.rs').read_text()
 if lane=='source':s+=(H/'prototype-tests.rs').read_text()
 p.write_text(s)
