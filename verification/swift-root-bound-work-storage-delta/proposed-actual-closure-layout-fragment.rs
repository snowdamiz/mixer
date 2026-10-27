// PROPOSAL ONLY. Replace exactly the original inline dispatch expression in a
// diagnostic scratch copy. The closure body/capture expression stays exact.
// Deliberate E0512 source-size diagnostics; no code can run or metadata qualify.
        let action = || run_prepaid_admitted_fixture_v1(fixture, attempt, expected);
        #[repr(C)]
        struct ClosureAlignmentProbeV1<T> { leading: u8, actual: T }
        fn uninitialized_shape_v1<T>(_: &T) -> std::mem::MaybeUninit<T> {
            std::mem::MaybeUninit::uninit()
        }
        let _size_diagnostic: [u8; 0] = unsafe {
            std::mem::transmute(uninitialized_shape_v1(&action))
        };
        let _alignment_diagnostic: [u8; 0] = unsafe {
            std::mem::transmute(ClosureAlignmentProbeV1 {
                leading: 0u8, actual: uninitialized_shape_v1(&action),
            })
        };
        Ok(reservation.dispatch_v1(action))
