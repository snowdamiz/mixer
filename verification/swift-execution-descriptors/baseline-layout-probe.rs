// Appended only to a disposable baseline checkout by qualify.py.
#[cfg(test)]
mod descriptor_baseline_layout_probe {
    use super::*;
    #[test]
    fn descriptor_baseline_layouts_match_frozen_target_expectations() {
        macro_rules! layout {
            ($ty:ty) => {
                (std::mem::size_of::<$ty>(), std::mem::align_of::<$ty>())
            };
        }
        assert_eq!(layout!(ValidatedSpans), (520, 8));
        assert_eq!(layout!(swift::ValidatedSwiftReactor), (664, 8));
        assert_eq!(layout!(Metadata), (352, 8));
        assert_eq!(layout!(Metadata<metadata::SwiftDeclaration>), (384, 8));
        assert_eq!(layout!(descriptors::SignatureView<'_>), (24, 8));
        assert_eq!(layout!(descriptors::GlobalView<'_>), (24, 8));
        assert_eq!(layout!(SegmentView<'_>), (24, 8));
        assert_eq!(layout!(policy::Policy<'_>), (8, 8));
        println!("baseline layouts (size, align): SwiftProof=(664,8); SwiftMetadata=(384,8); LegacyProof=(520,8); FrozenMetadata=(352,8); SignatureView=(24,8); GlobalView=(24,8); SegmentView=(24,8); Policy=(8,8)");
    }
}
