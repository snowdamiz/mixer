from pathlib import Path
p=Path(__file__).resolve().parent/'source/src/experimental_swift_reactor/cache_tests.rs'
s=p.read_text();assert s.count('actual_constructor_allocations=4')==1
p.write_text(s.replace('actual_constructor_allocations=4','actual_constructor_allocations=5'))
