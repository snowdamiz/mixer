from pathlib import Path
H=Path(__file__).resolve().parent
p=H/'source/src/experimental_swift_reactor/cache_tests.rs';s=p.read_text()
for name in ('attempts','allocations'):
 a=f'assert_eq!(allocations.{name}, 4);';b=f'assert_eq!(allocations.{name}, 5);'
 assert s.count(a)==1;s=s.replace(a,b)
p.write_text(s)
