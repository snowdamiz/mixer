from pathlib import Path
p=Path('verification/swift-selected-profile-adoption-independent/compiler-privacy/source/vm/src/experimental_swift_reactor')
for name,a,z in [('cache.rs',4835,4880),('cache/initial_profile_v1.rs',90,130),('retained_profile_loader_v1_tests.rs',535,565)]:
 s=(p/name).read_text().splitlines();print(name);print('\n'.join(f'{i+1}: {s[i]}' for i in range(a-1,z)))
