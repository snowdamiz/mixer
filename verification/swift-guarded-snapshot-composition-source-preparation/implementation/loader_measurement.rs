// Root-released append-only private measurement seam. No behavior calls.
#[cfg(mixer_snapshot_composition_layout)]
#[used]
static MIXER_COMPOSITION_LOADER_HELPER_LAYOUTS_V1:[usize;8]=[
 std::mem::size_of::<FileIdentityV1>(),std::mem::align_of::<FileIdentityV1>(), // FileIdentityV1
 std::mem::size_of::<std::iter::Enumerate<std::slice::Iter<'static,FileIdentityV1>>>(),std::mem::align_of::<std::iter::Enumerate<std::slice::Iter<'static,FileIdentityV1>>>(), // std::iter::Enumerate<std::slice::Iter<'static,FileIdentityV1>>
 std::mem::size_of::<(usize,&FileIdentityV1)>(),std::mem::align_of::<(usize,&FileIdentityV1)>(), // (usize,&FileIdentityV1)
 std::mem::size_of::<&FileIdentityV1>(),std::mem::align_of::<&FileIdentityV1>(), // &FileIdentityV1
];
