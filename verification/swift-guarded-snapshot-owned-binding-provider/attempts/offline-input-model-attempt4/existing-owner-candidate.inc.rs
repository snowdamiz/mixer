// PROPOSAL ONLY: conditional base is frozen lifetime candidate source146 tree
// 69068367d2eaf334d6881a624cac9142a0b4ecfeed50f23382724ae29e51d5e7.
// Its independent/root acceptance is pending. Not compiled/selected/operational.
// In particular, this module supplies no request, account, quote, admission,
// authenticated identity witness, or acquisition implementation.
#[cfg(target_os = "macos")]
mod existing_owner_candidate_v1 {
    use super::{
        ImmutableFixtureIdentitiesV1, PreexistingImmutableBindingV1,
        ReviewedFixtureBindingV1, SELECTED_SOURCE_BYTES_V1,
        SELECTED_SOURCE_SHA256_V1,
    };
    use std::os::unix::ffi::OsStrExt;

    // Logical input bytes only. Inline layouts, acquisition work/storage,
    // native opens and complete original diagnostics remain separate inputs.
    // Equal content, aliasing, moves and lifetimes give no backing credit.
    pub(super) struct InputBackingDescriptionV1 {
        pub(super) identity_bytes: [usize; 12],
        pub(super) native_path_bytes: [usize; 5],
        pub(super) separately_retained_path_bytes: [usize; 5],
        pub(super) logical_input_backing_bytes: usize,
    }

    pub(super) enum PendingUpstreamRequirementV1 { IndependentlyReviewedActualInputRequired }
    pub(super) struct PendingUpstreamRequirementsV1 {
        pub(super) acquisition_work: PendingUpstreamRequirementV1,
        pub(super) acquisition_inline_and_temporary_storage: PendingUpstreamRequirementV1,
        pub(super) acquisition_owned_backing: PendingUpstreamRequirementV1,
        pub(super) provider_work_and_inline_storage: PendingUpstreamRequirementV1,
        pub(super) original_diagnostic_pointee_backing: PendingUpstreamRequirementV1,
        pub(super) admitted_owner_and_authenticated_correspondence: PendingUpstreamRequirementV1,
    }

    // A candidate container is deliberately not an admitted-owner witness.
    // The entire input owner must already exist and remain immutable through
    // final result consumption. No capacity/hash label authenticates that fact.
    pub(super) struct UnqualifiedExistingOwnerCandidateV1<'p0> {
        pub(super) unqualified_binding: PreexistingImmutableBindingV1<'p0>,
        pub(super) input_backing: InputBackingDescriptionV1,
        pub(super) upstream: PendingUpstreamRequirementsV1,
    }

    pub(super) enum CandidateShapeRefusalV1 {
        EmptyIdentity { position: usize },
        SelectedSourceConstraintMismatch,
        EmptyNativePath { position: usize },
        NativePathContainsNul { position: usize },
        RetainedPathMismatch { position: usize },
        LogicalBackingOverflow,
    }

    // Borrow-only construction from a pre-existing owner. No acquisition,
    // hashing callback, allocation, leak, mutation, File call or fresh claim.
    // SHA256 fields retain their input values. Exact cryptographic validation
    // and source/build/session/launcher correspondence remain upstream Pending;
    // the existing loader's private platform hash is not callable from here.
    pub(super) fn describe_existing_owner_candidate_v1<'p0>(
        binding: ReviewedFixtureBindingV1<'p0>,
        identities: ImmutableFixtureIdentitiesV1<'p0>,
        native_path_bodies: [&'p0 [u8]; 5],
    ) -> Result<UnqualifiedExistingOwnerCandidateV1<'p0>, CandidateShapeRefusalV1> {
        let identities_in_order = [
            &identities.source, &identities.build, &identities.session,
            &identities.executable, &identities.compiler,
            &identities.compiler_version, &identities.compile_manifest,
            &identities.compile_argv, &identities.compile_environment,
            &identities.process_argv, &identities.process_environment,
            &identities.review,
        ];
        let mut identity_bytes = [0usize; 12];
        let mut logical_input_backing_bytes = 0usize;
        for position in 0..12 {
            let bytes = identities_in_order[position].bytes.len();
            if bytes == 0 {
                return Err(CandidateShapeRefusalV1::EmptyIdentity { position });
            }
            identity_bytes[position] = bytes;
            logical_input_backing_bytes = logical_input_backing_bytes
                .checked_add(bytes)
                .ok_or(CandidateShapeRefusalV1::LogicalBackingOverflow)?;
        }
        // These are only selected length/claim constraints. No hash check is
        // silently inferred from them and no fixture proof is constructed.
        if identities.source.bytes.len() != SELECTED_SOURCE_BYTES_V1
            || identities.source.sha256 != SELECTED_SOURCE_SHA256_V1
        {
            return Err(CandidateShapeRefusalV1::SelectedSourceConstraintMismatch);
        }

        let mut native_path_bytes = [0usize; 5];
        let mut separately_retained_path_bytes = [0usize; 5];
        for position in 0..5 {
            let actual_native = binding.paths[position].as_os_str().as_bytes();
            if actual_native.is_empty() {
                return Err(CandidateShapeRefusalV1::EmptyNativePath { position });
            }
            if actual_native.contains(&0) {
                return Err(CandidateShapeRefusalV1::NativePathContainsNul { position });
            }
            if actual_native != native_path_bodies[position] {
                return Err(CandidateShapeRefusalV1::RetainedPathMismatch { position });
            }
            native_path_bytes[position] = actual_native.len();
            separately_retained_path_bytes[position] = native_path_bodies[position].len();
            // Both copies are charged even if their pointers/content alias.
            logical_input_backing_bytes = logical_input_backing_bytes
                .checked_add(actual_native.len())
                .and_then(|n| n.checked_add(native_path_bodies[position].len()))
                .ok_or(CandidateShapeRefusalV1::LogicalBackingOverflow)?;
        }

        use PendingUpstreamRequirementV1::IndependentlyReviewedActualInputRequired as Pending;
        Ok(UnqualifiedExistingOwnerCandidateV1 {
            unqualified_binding: PreexistingImmutableBindingV1 {
                binding, native_path_bodies, identities,
            },
            input_backing: InputBackingDescriptionV1 {
                identity_bytes, native_path_bytes, separately_retained_path_bytes,
                logical_input_backing_bytes,
            },
            upstream: PendingUpstreamRequirementsV1 {
                acquisition_work: Pending,
                acquisition_inline_and_temporary_storage: Pending,
                acquisition_owned_backing: Pending,
                provider_work_and_inline_storage: Pending,
                original_diagnostic_pointee_backing: Pending,
                admitted_owner_and_authenticated_correspondence: Pending,
            },
        })
    }
}
