// Actual private ownership core. Native startup/allocator/source authority is
// intentionally unselected; integer prices and test guards cannot select it.
mod prepaid_input_owner_v1 {
    use super::*;
    use std::cell::Cell;
    use std::path::Path;
    use crate::experimental_swift_reactor::cache::SnapshotClaimsV1 as UnverifiedProfileDigestBytesV1;

    #[derive(Clone, Copy, Debug, PartialEq, Eq)]
    pub(in crate::experimental_swift_reactor) enum BootstrapFailureV1 {
        BootstrapPolicyPending, NativeStartupBridgePending, NativeAllocatorBridgePending,
        CompileClosureAuthorityPending, Overflow, InsufficientAcquisitionWork,
        InsufficientCleanupWork, InsufficientStorage, AlreadyReserved, AlreadyAttempted,
        Incomplete, AliasedIdentity, Extent, Offset, Packet, Nul, MetadataChanged,
        Io, Allocation, ShortInput, ExtraInput, Attempts, OverreportedRead,
        Record, Digest, BodyRole, LiveOwner, Correlation(usize), RetirementIncomplete,
    }
    // Complete originals are retained, never formatted/coerced into a scalar.
    struct OriginalAcquisitionFailureV1 {
        kind: BootstrapFailureV1, slot: usize, offset: usize, attempts: u32,
        io: Option<io::Error>, allocation: Option<std::collections::TryReserveError>,
        loader: Option<LoaderFailureV1>,
    }
    impl OriginalAcquisitionFailureV1 {
        fn new(kind: BootstrapFailureV1, slot: usize) -> Self {
            Self { kind, slot, offset: 0, attempts: 0, io: None, allocation: None, loader: None }
        }
        fn io(slot: usize, offset: usize, attempts: u32, original: io::Error) -> Self {
            Self { io: Some(original), offset, attempts, ..Self::new(BootstrapFailureV1::Io, slot) }
        }
    }
    struct FixtureBootstrapPolicyV1 {
        role_caps: [usize; 12], path_caps: [usize; 5], packet_cap: usize,
        validation: SwiftValidationBudget, product: SwiftRunBudget,
        allocation_slack: usize, original_failure_backing: usize,
        bridge: BridgePricesV1,
    }
    impl FixtureBootstrapPolicyV1 {
        fn selected_fixture_v1() -> Result<Self, BootstrapFailureV1> {
            Err(BootstrapFailureV1::BootstrapPolicyPending)
        }
    }
    #[derive(Clone, Copy)]
    struct BridgePricesV1 {
        metadata: u64, offset: u64, allocation: u64, read: u64, hash_per_byte: u64,
        path_per_byte: u64, correlation: u64, correlation_storage: u64, retirement: u64,
    }
    struct ReviewedAcquisitionQuoteV1 { acquisition_work: u64, cleanup_work: u64, peak_storage: u64 }
    #[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
    struct BootstrapUsageV1 { work: u64, storage: u64, peak: u64 }
    pub(in crate::experimental_swift_reactor) struct BootstrapLedgerV1 {
        policy: FixtureBootstrapPolicyV1, work_limit: u64, storage_limit: u64,
        usage: Cell<BootstrapUsageV1>, reserved: Cell<bool>,
    }
    impl BootstrapLedgerV1 {
        pub(in crate::experimental_swift_reactor) fn from_preexisting_fixture_startup_v1() -> Result<Self, BootstrapFailureV1> {
            // This call has no argument-derived policy, File call or allocation.
            let _policy = FixtureBootstrapPolicyV1::selected_fixture_v1()?;
            Err(BootstrapFailureV1::NativeStartupBridgePending)
        }
        fn reserve_before_any_input_effect_v1(&self, quote: ReviewedAcquisitionQuoteV1)
            -> Result<AcquisitionReservationV1<'_>, BootstrapFailureV1>
        {
            if self.reserved.get() { return Err(BootstrapFailureV1::AlreadyReserved); }
            if quote.acquisition_work == 0 || quote.cleanup_work == 0 || quote.peak_storage == 0 {
                return Err(BootstrapFailureV1::Incomplete);
            }
            let old = self.usage.get();
            let total = quote.acquisition_work.checked_add(quote.cleanup_work).ok_or(BootstrapFailureV1::Overflow)?;
            let work = old.work.checked_add(total).ok_or(BootstrapFailureV1::Overflow)?;
            let storage = old.storage.checked_add(quote.peak_storage).ok_or(BootstrapFailureV1::Overflow)?;
            if work > self.work_limit { return Err(BootstrapFailureV1::InsufficientAcquisitionWork); }
            if storage > self.storage_limit { return Err(BootstrapFailureV1::InsufficientStorage); }
            self.usage.set(BootstrapUsageV1 { work, storage, peak: old.peak.max(storage) });
            self.reserved.set(true);
            Ok(AcquisitionReservationV1 { root: self, operation_left: quote.acquisition_work,
                cleanup_left: quote.cleanup_work, storage_left: quote.peak_storage,
                original_storage: quote.peak_storage })
        }
    }
    // Affine, no Clone/Copy, no renewal and no work-refund path.
    struct AcquisitionReservationV1<'root> {
        root: &'root BootstrapLedgerV1, operation_left: u64, cleanup_left: u64,
        storage_left: u64, original_storage: u64,
    }
    struct PaidOperationV1<'root> { _root: &'root BootstrapLedgerV1 }
    impl<'root> AcquisitionReservationV1<'root> {
        fn operation_v1(&mut self, work: u64, storage: u64) -> Result<PaidOperationV1<'root>, BootstrapFailureV1> {
            if work == 0 { return Err(BootstrapFailureV1::Incomplete); }
            if work > self.operation_left { return Err(BootstrapFailureV1::InsufficientAcquisitionWork); }
            if storage > self.storage_left { return Err(BootstrapFailureV1::InsufficientStorage); }
            self.operation_left -= work;
            self.storage_left -= storage;
            Ok(PaidOperationV1 { _root: self.root })
        }
        fn cleanup_v1(&mut self) -> Result<PaidOperationV1<'root>, BootstrapFailureV1> {
            let work = self.root.policy.bridge.retirement;
            if work == 0 || work > self.cleanup_left { return Err(BootstrapFailureV1::InsufficientCleanupWork); }
            self.cleanup_left -= work;
            Ok(PaidOperationV1 { _root: self.root })
        }
    }
    struct ImmutableOwnedBytesV1 { bytes: Box<[u8]>, initialized: usize, allocation_bound: u64 }
    impl ImmutableOwnedBytesV1 {
        fn complete_v1(&self) -> bool { self.initialized == self.bytes.len() && !self.bytes.is_empty() }
        fn slice_v1(&self) -> &[u8] { &self.bytes[..self.initialized] }
    }
    struct NativePathBackingV1 {
        native: [Option<ImmutableOwnedBytesV1>; 5],
        retained: [Option<ImmutableOwnedBytesV1>; 5],
    }
    impl NativePathBackingV1 {
        fn empty_v1() -> Self { Self { native: std::array::from_fn(|_| None), retained: std::array::from_fn(|_| None) } }
    }
    struct RawSlotObligationV1 { slot: usize, checked: bool }
    // Raw never contains an integer that is converted to a File. Preowned means
    // an already-valid Rust owner, NOT authority to adopt an inherited raw slot.
    enum ActualInputSlotV1<R> {
        Raw(RawSlotObligationV1),
        Preowned { resource: R, initial: FileIdentityV1 },
        Owned(RetainedIdentityFileV1<R>), Retired,
    }
    struct RetainedIdentityFileV1<R> {
        role: usize, resource: R, initial: FileIdentityV1,
        body: Option<ImmutableOwnedBytesV1>, sha256: Option<[u8; 32]>,
    }
    struct PartialActualOwnersV1<R> {
        slots: [ActualInputSlotV1<R>; 13], adoption_bits: u16,
        paths: NativePathBackingV1, original: Option<OriginalAcquisitionFailureV1>,
        unresolved: bool,
    }
    impl<R> PartialActualOwnersV1<R> {
        fn all_owned_v1(&self) -> bool {
            self.adoption_bits == 0x1fff && !self.unresolved && self.slots.iter().all(|s| matches!(s, ActualInputSlotV1::Owned(_)))
        }
    }
    struct AcquiredUnverifiedOwnerV1<R> {
        partial: PartialActualOwnersV1<R>, claims: UnverifiedProfileDigestBytesV1,
    }
    #[must_use]
    struct PrepaidInputOwnerV1<'root, R> {
        reservation: AcquisitionReservationV1<'root>, actual: Option<AcquiredUnverifiedOwnerV1<R>>, retirement_started: bool,
    }
    // The trait is private, closed to external implementations. It selects no
    // authority. Every operation receives a consumed ticket before its effect.
    trait InputBridgeV1<R> {
        fn metadata_v1(&mut self, paid: PaidOperationV1<'_>, resource: &mut R, slot: usize)
            -> Result<FileIdentityV1, OriginalAcquisitionFailureV1>;
        fn offset_v1(&mut self, paid: PaidOperationV1<'_>, resource: &mut R, slot: usize)
            -> Result<u64, OriginalAcquisitionFailureV1>;
        fn allocate_v1(&mut self, paid: PaidOperationV1<'_>, count: usize, bound: u64, slot: usize)
            -> Result<ImmutableOwnedBytesV1, OriginalAcquisitionFailureV1>;
        fn read_v1(&mut self, paid: PaidOperationV1<'_>, resource: &mut R, output: &mut [u8]) -> io::Result<usize>;
        fn hash_v1(&mut self, paid: PaidOperationV1<'_>, bytes: &[u8], slot: usize)
            -> Result<[u8; 32], OriginalAcquisitionFailureV1>;
        fn retire_v1(&mut self, paid: PaidOperationV1<'_>, resource: R, slot: usize)
            -> Result<(), (R, OriginalAcquisitionFailureV1)>;
    }
    struct NativeInputBridgeV1;
    impl InputBridgeV1<File> for NativeInputBridgeV1 {
        fn metadata_v1(&mut self, _paid: PaidOperationV1<'_>, resource: &mut File, slot: usize)
            -> Result<FileIdentityV1, OriginalAcquisitionFailureV1> {
            #[cfg(target_os = "macos")]
            { identity(resource, Role::Source).map_err(|original| OriginalAcquisitionFailureV1 {
                loader: Some(original), ..OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Io, slot) }) }
            #[cfg(not(target_os = "macos"))]
            { let _ = resource; Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::NativeStartupBridgePending, slot)) }
        }
        fn offset_v1(&mut self, _paid: PaidOperationV1<'_>, resource: &mut File, slot: usize)
            -> Result<u64, OriginalAcquisitionFailureV1> {
            resource.stream_position().map_err(|e| OriginalAcquisitionFailureV1::io(slot, 0, 0, e))
        }
        fn allocate_v1(&mut self, _paid: PaidOperationV1<'_>, _count: usize, _bound: u64, slot: usize)
            -> Result<ImmutableOwnedBytesV1, OriginalAcquisitionFailureV1> {
            // std allocator capacity is NOT a pre-call slack/failure bound.
            Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::NativeAllocatorBridgePending, slot))
        }
        fn read_v1(&mut self, _paid: PaidOperationV1<'_>, resource: &mut File, output: &mut [u8]) -> io::Result<usize> {
            resource.read(output)
        }
        fn hash_v1(&mut self, _paid: PaidOperationV1<'_>, bytes: &[u8], slot: usize)
            -> Result<[u8; 32], OriginalAcquisitionFailureV1> {
            #[cfg(target_os = "macos")]
            { platform::hash(bytes, &mut LoaderUsageV1::default()).map_err(|original| OriginalAcquisitionFailureV1 {
                loader: Some(original), ..OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Io, slot) }) }
            #[cfg(not(target_os = "macos"))]
            { let _ = bytes; Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::NativeStartupBridgePending, slot)) }
        }
        fn retire_v1(&mut self, _paid: PaidOperationV1<'_>, resource: File, slot: usize)
            -> Result<(), (File, OriginalAcquisitionFailureV1)> {
            // File::drop cannot certify healthy native close. Keep owner.
            Err((resource, OriginalAcquisitionFailureV1::new(BootstrapFailureV1::RetirementIncomplete, slot)))
        }
    }
    fn store_failure_v1<R>(partial: &mut PartialActualOwnersV1<R>, original: OriginalAcquisitionFailureV1) {
        // First original wins; no later diagnosis replaces its backing.
        if partial.original.is_none() { partial.original = Some(original); }
    }
    fn adopt_preowned_slots_core_v1<R, B: InputBridgeV1<R>>(
        paid: &mut AcquisitionReservationV1<'_>, partial: &mut PartialActualOwnersV1<R>, bridge: &mut B,
    ) {
        for i in 0..13 {
            if partial.original.is_some() { return; }
            let ticket = match paid.operation_v1(paid.root.policy.bridge.metadata, 0) {
                Ok(t) => t, Err(e) => { store_failure_v1(partial, OriginalAcquisitionFailureV1::new(e, i)); return; }
            };
            let observed = match &mut partial.slots[i] {
                ActualInputSlotV1::Preowned { resource, .. } => bridge.metadata_v1(ticket, resource, i),
                _ => { partial.unresolved = true; store_failure_v1(partial,
                    OriginalAcquisitionFailureV1::new(BootstrapFailureV1::NativeStartupBridgePending, i)); return; }
            };
            let observed = match observed { Ok(v) => v, Err(e) => { store_failure_v1(partial, e); return; } };
            if observed.mode & 0o170000 != 0o100000 || observed.bytes == 0 {
                store_failure_v1(partial, OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Extent, i)); return;
            }
            for j in 0..i {
                if let ActualInputSlotV1::Owned(old) = &partial.slots[j] {
                    if (old.initial.dev, old.initial.inode) == (observed.dev, observed.inode) {
                        store_failure_v1(partial, OriginalAcquisitionFailureV1::new(BootstrapFailureV1::AliasedIdentity, i)); return;
                    }
                }
            }
            // No fallible gap after moving the represented resource. Raw slots
            // never take this branch, and no raw-FD conversion exists here.
            let old = std::mem::replace(&mut partial.slots[i], ActualInputSlotV1::Retired);
            match old {
                ActualInputSlotV1::Preowned { resource, initial } => {
                    partial.slots[i] = ActualInputSlotV1::Owned(RetainedIdentityFileV1 {
                        role: i, resource, initial, body: None, sha256: None });
                    partial.adoption_bits |= 1 << i;
                    if initial != observed { store_failure_v1(partial,
                        OriginalAcquisitionFailureV1::new(BootstrapFailureV1::MetadataChanged, i)); return; }
                }
                other => { partial.slots[i] = other; partial.unresolved = true; return; }
            }
        }
    }
    fn allocation_bound_v1(count: usize, policy: &FixtureBootstrapPolicyV1) -> Result<u64, BootstrapFailureV1> {
        let n = count.checked_add(policy.allocation_slack)
            .and_then(|n| n.checked_add(policy.original_failure_backing)).ok_or(BootstrapFailureV1::Overflow)?;
        u64::try_from(n).map_err(|_| BootstrapFailureV1::Overflow)
    }
    fn read_owned_body_once_v1<R, B: InputBridgeV1<R>>(
        paid: &mut AcquisitionReservationV1<'_>, owned: &mut RetainedIdentityFileV1<R>, cap: usize, bridge: &mut B,
    ) -> Result<(), OriginalAcquisitionFailureV1> {
        let slot = owned.role;
        if owned.body.is_some() { return Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::AlreadyAttempted, slot)); }
        let price = paid.root.policy.bridge;
        let effect = |kind| OriginalAcquisitionFailureV1::new(kind, slot);
        let t = paid.operation_v1(price.metadata, 0).map_err(effect)?;
        let initial = bridge.metadata_v1(t, &mut owned.resource, slot)?;
        if initial != owned.initial || initial.mode & 0o170000 != 0o100000 {
            return Err(effect(BootstrapFailureV1::MetadataChanged));
        }
        let t = paid.operation_v1(price.offset, 0).map_err(effect)?;
        if bridge.offset_v1(t, &mut owned.resource, slot)? != 0 { return Err(effect(BootstrapFailureV1::Offset)); }
        let count = usize::try_from(initial.bytes).map_err(|_| effect(BootstrapFailureV1::Extent))?;
        if count == 0 || count > cap { return Err(effect(BootstrapFailureV1::Extent)); }
        let bound = allocation_bound_v1(count, &paid.root.policy).map_err(effect)?;
        let t = paid.operation_v1(price.allocation, bound).map_err(effect)?;
        let backing = bridge.allocate_v1(t, count, bound, slot)?;
        // Move initialized/partial allocation into its original File owner BEFORE
        // reads or any subsequent fallible check; errors borrow, never consume it.
        owned.body = Some(backing);
        let body = owned.body.as_mut().expect("just stored private backing");
        if body.bytes.len() != count || body.initialized != 0 || body.allocation_bound > bound {
            return Err(effect(BootstrapFailureV1::Allocation));
        }
        for base in (0..count).step_by(BLOCK) {
            let end = count.min(base + BLOCK);
            let mut used = 0;
            let mut complete = false;
            for attempt in 1..=ATTEMPTS {
                let t = paid.operation_v1(price.read, 0).map_err(effect)?;
                match bridge.read_v1(t, &mut owned.resource, &mut body.bytes[base + used..end]) {
                    Ok(n) if n > end - base - used => return Err(OriginalAcquisitionFailureV1 {
                        offset: base + used, attempts: attempt, ..effect(BootstrapFailureV1::OverreportedRead) }),
                    Ok(0) => return Err(OriginalAcquisitionFailureV1 {
                        offset: base + used, attempts: attempt, ..effect(BootstrapFailureV1::ShortInput) }),
                    Ok(n) => { used += n; body.initialized = base + used;
                        if base + used == end { complete = true; break; } }
                    Err(e) if e.kind() == io::ErrorKind::Interrupted => {}
                    Err(e) => return Err(OriginalAcquisitionFailureV1::io(slot, base + used, attempt, e)),
                }
            }
            if !complete { return Err(OriginalAcquisitionFailureV1 {
                offset: base + used, attempts: ATTEMPTS, ..effect(BootstrapFailureV1::Attempts) }); }
        }
        let mut eof = [0u8; 1];
        let mut complete = false;
        for attempt in 1..=ATTEMPTS {
            let t = paid.operation_v1(price.read, 0).map_err(effect)?;
            match bridge.read_v1(t, &mut owned.resource, &mut eof) {
                Ok(0) => { complete = true; break; }
                Ok(1) => return Err(effect(BootstrapFailureV1::ExtraInput)),
                Ok(_) => return Err(effect(BootstrapFailureV1::OverreportedRead)),
                Err(e) if e.kind() == io::ErrorKind::Interrupted => {}
                Err(e) => return Err(OriginalAcquisitionFailureV1::io(slot, count, attempt, e)),
            }
        }
        if !complete { return Err(effect(BootstrapFailureV1::Attempts)); }
        let t = paid.operation_v1(price.metadata, 0).map_err(effect)?;
        if bridge.metadata_v1(t, &mut owned.resource, slot)? != initial { return Err(effect(BootstrapFailureV1::MetadataChanged)); }
        let hash_work = price.hash_per_byte.checked_mul(count as u64).ok_or_else(|| effect(BootstrapFailureV1::Overflow))?;
        let t = paid.operation_v1(hash_work, 0).map_err(effect)?;
        owned.sha256 = Some(bridge.hash_v1(t, body.slice_v1(), slot)?);
        Ok(())
    }
    fn decode_path_packet_v1<'a>(packet: &'a [u8], policy: &FixtureBootstrapPolicyV1)
        -> Result<[&'a [u8]; 5], BootstrapFailureV1>
    {
        if packet.len() < 64 || packet.len() > policy.packet_cap || &packet[..8] != b"MIXPTH01"
            || word(packet, 8) != 1 || word(packet, 16) != packet.len() as u64 { return Err(BootstrapFailureV1::Packet); }
        let mut out = [&[][..]; 5]; let mut at = 64usize;
        for i in 0..5 {
            let n = usize::try_from(word(packet, 24 + i * 8)).map_err(|_| BootstrapFailureV1::Extent)?;
            let end = at.checked_add(n).ok_or(BootstrapFailureV1::Overflow)?;
            if n == 0 || n > policy.path_caps[i] || end > packet.len() { return Err(BootstrapFailureV1::Extent); }
            let bytes = &packet[at..end];
            if bytes.contains(&0) { return Err(BootstrapFailureV1::Nul); }
            out[i] = bytes; at = end;
        }
        if at != packet.len() { return Err(BootstrapFailureV1::Packet); }
        Ok(out)
    }
    fn copy_native_paths_once_v1<R, B: InputBridgeV1<R>>(
        paid: &mut AcquisitionReservationV1<'_>, paths: [&[u8]; 5], output: &mut NativePathBackingV1, bridge: &mut B,
    ) -> Result<(), OriginalAcquisitionFailureV1> {
        for i in 0..5 {
            for native in [true, false] {
                let place = if native { &mut output.native[i] } else { &mut output.retained[i] };
                let fail = |kind| OriginalAcquisitionFailureV1::new(kind, 13 + i);
                if place.is_some() { return Err(fail(BootstrapFailureV1::AlreadyAttempted)); }
                let n = paths[i].len();
                if n == 0 || n > paid.root.policy.path_caps[i] || paths[i].contains(&0) { return Err(fail(BootstrapFailureV1::Extent)); }
                let bound = allocation_bound_v1(n, &paid.root.policy).map_err(fail)?;
                let t = paid.operation_v1(paid.root.policy.bridge.allocation, bound).map_err(fail)?;
                *place = Some(bridge.allocate_v1(t, n, bound, 13 + i)?);
                let owned = place.as_mut().expect("stored before fallible copy prepay");
                if owned.bytes.len() != n || owned.initialized != 0 || owned.allocation_bound > bound { return Err(fail(BootstrapFailureV1::Allocation)); }
                let work = paid.root.policy.bridge.path_per_byte.checked_mul(n as u64).ok_or_else(|| fail(BootstrapFailureV1::Overflow))?;
                let _paid = paid.operation_v1(work, 0).map_err(fail)?;
                owned.bytes.copy_from_slice(paths[i]); owned.initialized = n;
            }
        }
        Ok(())
    }
    // Production acquisition cannot manufacture File ownership. All thirteen raw
    // obligations enter the carrier before the missing bridge refusal is stored.
    fn acquire_inherited_inputs_once_v1<'root>(paid: AcquisitionReservationV1<'root>, claims: UnverifiedProfileDigestBytesV1)
        -> PrepaidInputOwnerV1<'root, File>
    {
        let mut partial = PartialActualOwnersV1 { slots: std::array::from_fn(|slot|
            ActualInputSlotV1::Raw(RawSlotObligationV1 { slot, checked: false })),
            adoption_bits: 0, paths: NativePathBackingV1::empty_v1(), original: None, unresolved: true };
        store_failure_v1(&mut partial, OriginalAcquisitionFailureV1::new(BootstrapFailureV1::NativeStartupBridgePending, 0));
        PrepaidInputOwnerV1 { reservation: paid, actual: Some(AcquiredUnverifiedOwnerV1 { partial, claims }), retirement_started: false }
    }
    // Compiled File specialization of all executable ownership/read/path cores.
    // No caller can reach this without a privately selected root and valid owners.
    fn read_preowned_file_set_once_v1(owner: &mut PrepaidInputOwnerV1<'_, File>) {
        let mut bridge = NativeInputBridgeV1;
        let actual = match owner.actual.as_mut() { Some(v) => v, None => return };
        adopt_preowned_slots_core_v1(&mut owner.reservation, &mut actual.partial, &mut bridge);
        for i in 0..13 {
            if actual.partial.original.is_some() { return; }
            let cap = if i < 12 { owner.reservation.root.policy.role_caps[i] } else { owner.reservation.root.policy.packet_cap };
            let result = match &mut actual.partial.slots[i] {
                ActualInputSlotV1::Owned(file) => read_owned_body_once_v1(&mut owner.reservation, file, cap, &mut bridge),
                _ => Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Incomplete, i)),
            };
            if let Err(original) = result { store_failure_v1(&mut actual.partial, original); return; }
        }
        let packet = match &actual.partial.slots[12] {
            ActualInputSlotV1::Owned(file) => file.body.as_ref().expect("read success stored body").slice_v1(), _ => return,
        };
        let paths = match decode_path_packet_v1(packet, &owner.reservation.root.policy) {
            Ok(v) => v, Err(kind) => { store_failure_v1(&mut actual.partial, OriginalAcquisitionFailureV1::new(kind, 12)); return; }
        };
        if let Err(original) = copy_native_paths_once_v1(&mut owner.reservation, paths, &mut actual.partial.paths, &mut bridge) {
            store_failure_v1(&mut actual.partial, original);
        }
    }
    fn owned_file_v1<R>(actual: &AcquiredUnverifiedOwnerV1<R>, i: usize) -> Result<&RetainedIdentityFileV1<R>, BootstrapFailureV1> {
        match &actual.partial.slots[i] { ActualInputSlotV1::Owned(v) => Ok(v), _ => Err(BootstrapFailureV1::Incomplete) }
    }
    fn body_v1<R>(actual: &AcquiredUnverifiedOwnerV1<R>, i: usize) -> Result<&[u8], BootstrapFailureV1> {
        let f = owned_file_v1(actual, i)?;
        match &f.body { Some(v) if v.complete_v1() && f.role == i && f.initial.bytes == v.bytes.len() as u64 => Ok(v.slice_v1()),
            _ => Err(BootstrapFailureV1::BodyRole) }
    }
    fn decode_identity_v1(bytes: &[u8]) -> Result<FileIdentityV1, BootstrapFailureV1> {
        if bytes.len() != 64 { return Err(BootstrapFailureV1::Record); }
        let identity = FileIdentityV1 { dev: word(bytes, 0), inode: word(bytes, 8), bytes: word(bytes, 16),
            mode: word(bytes, 24), mtime: word(bytes, 32) as i64, mtime_ns: word(bytes, 40) as i64,
            ctime: word(bytes, 48) as i64, ctime_ns: word(bytes, 56) as i64 };
        if identity.bytes == 0 || identity.mode & 0o170000 != 0o100000 { return Err(BootstrapFailureV1::Record); }
        Ok(identity)
    }
    // Nine groups are derived from live owned production records, never a map.
    fn derive_provenance_v1<R>(actual: &AcquiredUnverifiedOwnerV1<R>, policy: &FixtureBootstrapPolicyV1)
        -> Result<LoaderProvenanceV1, OriginalAcquisitionFailureV1>
    {
        let fail = |kind| OriginalAcquisitionFailureV1::new(kind, 2);
        if !actual.partial.all_owned_v1() || actual.partial.original.is_some() { return Err(fail(BootstrapFailureV1::Incomplete)); }
        for i in 0..13 { let _ = body_v1(actual, i).map_err(fail)?; }
        let build = body_v1(actual, 1).map_err(fail)?;
        let session = body_v1(actual, 2).map_err(fail)?;
        let b = parse_build(build).map_err(|original| OriginalAcquisitionFailureV1 { loader: Some(original), ..fail(BootstrapFailureV1::Record) })?;
        let s = parse_session(session).map_err(|original| OriginalAcquisitionFailureV1 { loader: Some(original), ..fail(BootstrapFailureV1::Record) })?;
        let mut ids = [FileIdentityV1::default(); 4];
        for (i, output) in ids.iter_mut().enumerate() { *output = owned_file_v1(actual, i).map_err(fail)?.initial; }
        let digest = |i| owned_file_v1(actual, i).and_then(|f| f.sha256.ok_or(BootstrapFailureV1::Digest));
        let source = digest(0).map_err(fail)?; let build_digest = digest(1).map_err(fail)?;
        let session_digest = digest(2).map_err(fail)?; let executable = digest(3).map_err(fail)?;
        let manifest = digest(6).map_err(fail)?;
        if s.source_bytes == 0 || s.budget.source_bytes == 0 || s.budget.metadata_bytes == 0
            || s.budget.scratch_bytes == 0 || s.budget.work_credits == 0 || s.budget.deadline_ms == 0
            || s.source_bytes != ids[0].bytes || decode_identity_v1(s.sections[0].bytes).map_err(fail)? != ids[0]
            || s.budget != policy.validation || !budget_valid(s.budget) || s.source != source || s.build != build_digest
            || s.executable != executable || b.digests[0] != manifest || b.digests[5] != executable
            || b.output_bytes != ids[3].bytes { return Err(fail(BootstrapFailureV1::Record)); }
        // Complete byte-level record/body joins retain binary ordering.
        for (part, slot) in [(0,6), (1,7), (2,8), (3,5)] {
            if b.sections[part].bytes != body_v1(actual, slot).map_err(fail)? || b.digests[part] != digest(slot).map_err(fail)? {
                return Err(fail(BootstrapFailureV1::Digest));
            }
        }
        if b.digests[4] != digest(4).map_err(fail)? || s.sections[1].bytes != body_v1(actual, 9).map_err(fail)?
            || s.sections[2].bytes != body_v1(actual, 10).map_err(fail)? { return Err(fail(BootstrapFailureV1::Digest)); }
        let paths = decode_path_packet_v1(body_v1(actual, 12).map_err(fail)?, policy).map_err(fail)?;
        for i in 0..5 {
            let native = actual.partial.paths.native[i].as_ref().ok_or_else(|| fail(BootstrapFailureV1::Incomplete))?;
            let retained = actual.partial.paths.retained[i].as_ref().ok_or_else(|| fail(BootstrapFailureV1::Incomplete))?;
            if !native.complete_v1() || !retained.complete_v1() || native.slice_v1() != paths[i] || retained.slice_v1() != paths[i] {
                return Err(fail(BootstrapFailureV1::Packet));
            }
        }
        Ok(LoaderProvenanceV1 { validation_budget: s.budget, source_extent: s.source_bytes, source, manifest,
            build: build_digest, session: session_digest, executable, nonce: s.nonce.try_into().expect("binary fixed width"), identities: ids })
    }
    // No production constructor exists for this witness. Concrete source-root
    // compile closure, external review, process/image and launcher custody must
    // first be independently selected; digest equality is never that witness.
    struct TrustedLocalLauncherCustodyV1 { _private: () }
    struct AdmittedImmutableOwnerCoreV1<'root,R> {
        owned: PrepaidInputOwnerV1<'root,R>, expected: LoaderProvenanceV1,
        custody: TrustedLocalLauncherCustodyV1, attempt_taken: Cell<bool>,
    }
    pub(in crate::experimental_swift_reactor) struct AdmittedImmutableOwnerV1<'root>(AdmittedImmutableOwnerCoreV1<'root,File>);
    enum OwnedAdmissionCoreOutcomeV1<'root,R> {
        Admitted(AdmittedImmutableOwnerCoreV1<'root,R>), Refused(PrepaidInputOwnerV1<'root,R>),
    }
    fn verify_actual_bodies_core_v1<R,B:InputBridgeV1<R>>(paid:&mut AcquisitionReservationV1<'_>,actual:&mut AcquiredUnverifiedOwnerV1<R>,bridge:&mut B)
        -> Result<LoaderProvenanceV1,OriginalAcquisitionFailureV1>
    {
        if actual.partial.original.is_some() { return Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Incomplete,0)); }
        for i in 0..13 {
            let fail=|kind|OriginalAcquisitionFailureV1::new(kind,i);
            let owned=match &mut actual.partial.slots[i] { ActualInputSlotV1::Owned(v)=>v,_=>return Err(fail(BootstrapFailureV1::Incomplete)) };
            let t=paid.operation_v1(paid.root.policy.bridge.metadata,0).map_err(fail)?;
            if bridge.metadata_v1(t,&mut owned.resource,i)?!=owned.initial { return Err(fail(BootstrapFailureV1::MetadataChanged)); }
            let body=match owned.body.as_ref() {Some(v) if v.complete_v1()=>v,_=>return Err(fail(BootstrapFailureV1::Incomplete))};
            let work=paid.root.policy.bridge.hash_per_byte.checked_mul(body.bytes.len() as u64).ok_or_else(||fail(BootstrapFailureV1::Overflow))?;
            let t=paid.operation_v1(work,0).map_err(fail)?;
            if Some(bridge.hash_v1(t,body.slice_v1(),i)?)!=owned.sha256 {return Err(fail(BootstrapFailureV1::Digest));}
        }
        let bytes=body_v1(actual,1).map_err(|kind|OriginalAcquisitionFailureV1::new(kind,1))?.len()
            .checked_add(body_v1(actual,2).map_err(|kind|OriginalAcquisitionFailureV1::new(kind,2))?.len())
            .and_then(|n|n.checked_add(64)).ok_or_else(||OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Overflow,1))?;
        let _paid=paid.operation_v1(bytes as u64,0).map_err(|kind|OriginalAcquisitionFailureV1::new(kind,1))?;
        derive_provenance_v1(actual,&paid.root.policy)
    }
    fn complete_admission_core_v1<'root,R,B:InputBridgeV1<R>>(mut owned: PrepaidInputOwnerV1<'root,R>, custody: TrustedLocalLauncherCustodyV1,bridge:&mut B)
        -> OwnedAdmissionCoreOutcomeV1<'root,R>
    {
        let derived = match owned.actual.as_mut() {
            Some(actual) => verify_actual_bodies_core_v1(&mut owned.reservation,actual,bridge),
            None => Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Incomplete,0)),
        };
        let expected = match derived {
            Ok(expected) => expected,
            Err(original) => {
                if let Some(actual) = owned.actual.as_mut() { store_failure_v1(&mut actual.partial,original); }
                return OwnedAdmissionCoreOutcomeV1::Refused(owned);
            }
        };
        let prices = owned.reservation.root.policy.bridge;
        // Entire fixed ingress/call/result/refusal overlap debited from the
        // original acquisition partition BEFORE admission publication.
        if let Err(kind) = owned.reservation.operation_v1(prices.correlation, prices.correlation_storage) {
            if let Some(actual) = owned.actual.as_mut() { store_failure_v1(&mut actual.partial,
                OriginalAcquisitionFailureV1::new(kind,13)); }
            return OwnedAdmissionCoreOutcomeV1::Refused(owned);
        }
        OwnedAdmissionCoreOutcomeV1::Admitted(AdmittedImmutableOwnerCoreV1 {
            owned, expected, custody, attempt_taken: Cell::new(false) })
    }
    fn verify_owned_once_v1<'root>(mut owner: PrepaidInputOwnerV1<'root,File>) -> OwnedAdmissionCoreOutcomeV1<'root,File> {
        let result = match owner.actual.as_mut() {
            Some(actual) => verify_actual_bodies_core_v1(&mut owner.reservation,actual,&mut NativeInputBridgeV1),
            None => Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Incomplete,0)),
        };
        let original = match result { Err(e) => e, Ok(_) => OriginalAcquisitionFailureV1::new(BootstrapFailureV1::CompileClosureAuthorityPending,11) };
        if let Some(actual) = owner.actual.as_mut() { store_failure_v1(&mut actual.partial,original); }
        // No production TrustedLocalLauncherCustodyV1 producer exists.
        OwnedAdmissionCoreOutcomeV1::Refused(owner)
    }
    pub(in crate::experimental_swift_reactor) fn selected_bootstrap_ledger_v1()
        -> Result<BootstrapLedgerV1, BootstrapFailureV1>
    {
        BootstrapLedgerV1::from_preexisting_fixture_startup_v1()
    }
    pub(in crate::experimental_swift_reactor) struct BorrowedOwnerDataV1<'owner> {
        pub(in crate::experimental_swift_reactor) identities: [(&'owner [u8], [u8;32]);12],
        pub(in crate::experimental_swift_reactor) paths: [&'owner Path;5],
        pub(in crate::experimental_swift_reactor) retained_paths: [&'owner [u8];5],
        pub(in crate::experimental_swift_reactor) claims: &'owner UnverifiedProfileDigestBytesV1,
        pub(in crate::experimental_swift_reactor) validation: SwiftValidationBudget,
        pub(in crate::experimental_swift_reactor) product: SwiftRunBudget,
    }
    pub(in crate::experimental_swift_reactor) struct AdmittedLoaderCorrespondenceV1<'owner> {
        owner_data: &'owner LoaderProvenanceV1,
    }
    pub(in crate::experimental_swift_reactor) struct PrepaidCorrelationAttemptV1<'owner> {
        expected: &'owner LoaderProvenanceV1, live: &'owner Cell<bool>,
    }
    impl<R> AdmittedImmutableOwnerCoreV1<'_,R> {
        fn correlation_scope_core_v1(&self)
            -> Result<(AdmittedLoaderCorrespondenceV1<'_>, PrepaidCorrelationAttemptV1<'_>), BootstrapFailureV1>
        {
            if self.attempt_taken.replace(true) { return Err(BootstrapFailureV1::AlreadyAttempted); }
            Ok((AdmittedLoaderCorrespondenceV1 { owner_data: &self.expected },
                PrepaidCorrelationAttemptV1 { expected: &self.expected, live: &self.attempt_taken }))
        }
    }
    impl AdmittedImmutableOwnerV1<'_> {
        pub(in crate::experimental_swift_reactor) fn scoped_binding_v1(&self) -> BorrowedOwnerDataV1<'_> {
            use std::os::unix::ffi::OsStrExt;
            let actual = self.0.owned.actual.as_ref().expect("private admitted invariant");
            BorrowedOwnerDataV1 { identities: std::array::from_fn(|i| (body_v1(actual, i).expect("admitted body"),
                    owned_file_v1(actual, i).expect("admitted file").sha256.expect("admitted hash"))),
                paths: std::array::from_fn(|i| Path::new(std::ffi::OsStr::from_bytes(
                    actual.partial.paths.native[i].as_ref().expect("admitted path").slice_v1()))),
                retained_paths: std::array::from_fn(|i| actual.partial.paths.retained[i].as_ref().expect("admitted retained path").slice_v1()),
                claims: &actual.claims, validation: self.0.owned.reservation.root.policy.validation,
                product: self.0.owned.reservation.root.policy.product }
        }
        pub(in crate::experimental_swift_reactor) fn correlation_scope_v1(&self)
            -> Result<(AdmittedLoaderCorrespondenceV1<'_>, PrepaidCorrelationAttemptV1<'_>), BootstrapFailureV1>
        {
            self.0.correlation_scope_core_v1()
        }
    }
    // Fixed typed actual carrier; the generic form substitutes ONLY File guards
    // in host tests. It never substitutes the real validator proof/provenance.
    struct LoaderCarrierCoreV1<R> {
        selected: Result<SelectedValidatedProfileV1, LoaderFailureV1>,
        files: [R;3], executable: Option<R>, usage: LoaderUsageV1,
    }
    pub(in crate::experimental_swift_reactor) struct SuppliedLoaderCarrierV1 { original: LoaderOutcomeV1 }
    impl SuppliedLoaderCarrierV1 {
        pub(in crate::experimental_swift_reactor) fn retain_complete_v1(original: LoaderOutcomeV1) -> Self { Self { original } }
    }
    pub(in crate::experimental_swift_reactor) struct CorrelatedSelectedProfileV1(SelectedValidatedProfileV1);
    impl CorrelatedSelectedProfileV1 {
        pub(in crate::experimental_swift_reactor) fn into_selected_v1(self) -> SelectedValidatedProfileV1 { self.0 }
    }
    pub(in crate::experimental_swift_reactor) struct OriginalCorrelationRefusalV1 { kind: BootstrapFailureV1, retained_selection: Option<Result<SelectedValidatedProfileV1,LoaderFailureV1>> }
    pub(in crate::experimental_swift_reactor) enum OwnedCorrelationOutcomeV1 {
        Correlated { selected: CorrelatedSelectedProfileV1, files: ReturnedLoaderFilesV1, usage: LoaderUsageV1 },
        LoaderRefused { original: LoaderFailureV1, files: ReturnedLoaderFilesV1, usage: LoaderUsageV1 },
        Refused { original: OriginalCorrelationRefusalV1, files: ReturnedLoaderFilesV1, usage: LoaderUsageV1 },
    }
    fn same_provenance_group_v1(a: &LoaderProvenanceV1, b: &LoaderProvenanceV1) -> Result<(), BootstrapFailureV1> {
        let groups = [a.source == b.source, a.manifest == b.manifest, a.build == b.build,
            a.session == b.session, a.executable == b.executable, a.nonce == b.nonce,
            a.validation_budget == b.validation_budget, a.source_extent == b.source_extent,
            a.identities == b.identities];
        for (i, same) in groups.into_iter().enumerate() { if !same { return Err(BootstrapFailureV1::Correlation(i)); } }
        if a.source_extent == 0 { return Err(BootstrapFailureV1::Correlation(7)); }
        Ok(())
    }
    fn correlate_core_v1<R>(attempt: PrepaidCorrelationAttemptV1<'_>, carrier: LoaderCarrierCoreV1<R>,
        expected: &AdmittedLoaderCorrespondenceV1<'_>) -> Result<LoaderCarrierCoreV1<R>, (OriginalCorrelationRefusalV1, LoaderCarrierCoreV1<R>)>
    {
        // COMPLETE original proof/result/files/usage already moved into carrier.
        let refusal = if !attempt.live.get() { Err(BootstrapFailureV1::LiveOwner) }
            else { same_provenance_group_v1(attempt.expected, expected.owner_data) };
        if let Err(kind) = refusal { return Err((OriginalCorrelationRefusalV1 { kind, retained_selection: None }, carrier)); }
        if let Ok(selected) = &carrier.selected {
            if let Err(kind) = same_provenance_group_v1(&selected.provenance, attempt.expected) {
                return Err((OriginalCorrelationRefusalV1 { kind, retained_selection: None }, carrier));
            }
        }
        Ok(carrier)
    }
    pub(in crate::experimental_swift_reactor) fn correlate_admitted_loader_v1(
        attempt: PrepaidCorrelationAttemptV1<'_>, carrier: SuppliedLoaderCarrierV1,
        expected: &AdmittedLoaderCorrespondenceV1<'_>,
    ) -> OwnedCorrelationOutcomeV1 {
        // First receive and retain the WHOLE outcome, then move it into the
        // fixed owning generic program. No fallible operation intervenes.
        let LoaderOutcomeV1 { selected, files, usage } = carrier.original;
        let ReturnedLoaderFilesV1 { source, build, session, executable } = files;
        let complete = LoaderCarrierCoreV1 { selected, files: [source,build,session], executable, usage };
        match correlate_core_v1(attempt, complete, expected) {
            Ok(LoaderCarrierCoreV1 { selected, files: [source,build,session], executable, usage }) => {
                let files = ReturnedLoaderFilesV1 { source,build,session,executable };
                match selected {
                    Ok(selected) => OwnedCorrelationOutcomeV1::Correlated { selected: CorrelatedSelectedProfileV1(selected), files, usage },
                    Err(original) => OwnedCorrelationOutcomeV1::LoaderRefused { original, files, usage },
                }
            }
            Err((mut original, LoaderCarrierCoreV1 { selected, files: [source,build,session], executable, usage })) => {
                original.retained_selection = Some(selected);
                OwnedCorrelationOutcomeV1::Refused { original, files: ReturnedLoaderFilesV1 { source,build,session,executable }, usage }
            }
        }
    }
    #[must_use]
    struct CompleteAcquisitionRetirementV1<'root> { paid: AcquisitionReservationV1<'root> }
    enum AcquisitionRetirementOutcomeV1<'root, R> {
        Complete(CompleteAcquisitionRetirementV1<'root>), Retained(PrepaidInputOwnerV1<'root, R>),
    }
    fn retire_acquired_owner_core_v1<'root, R, B: InputBridgeV1<R>>(
        mut owner: PrepaidInputOwnerV1<'root,R>, bridge: &mut B,
    ) -> AcquisitionRetirementOutcomeV1<'root,R> {
        if owner.retirement_started { return AcquisitionRetirementOutcomeV1::Retained(owner); }
        owner.retirement_started = true;
        let actual = match owner.actual.as_mut() { Some(v) => v, None => return AcquisitionRetirementOutcomeV1::Retained(owner) };
        // Never close raw/unresolved obligations or mint a complete token.
        if actual.partial.unresolved || actual.partial.slots.iter().any(|s| matches!(s,ActualInputSlotV1::Raw(_) | ActualInputSlotV1::Preowned {..})) {
            return AcquisitionRetirementOutcomeV1::Retained(owner);
        }
        for i in 0..13 {
            if matches!(actual.partial.slots[i], ActualInputSlotV1::Retired) { continue; }
            let t = match owner.reservation.cleanup_v1() {
                Ok(t) => t, Err(kind) => { store_failure_v1(&mut actual.partial, OriginalAcquisitionFailureV1::new(kind,i));
                    return AcquisitionRetirementOutcomeV1::Retained(owner); }
            };
            let slot = std::mem::replace(&mut actual.partial.slots[i], ActualInputSlotV1::Retired);
            if let ActualInputSlotV1::Owned(RetainedIdentityFileV1 { role, resource, initial, body, sha256 }) = slot {
                match bridge.retire_v1(t, resource, i) {
                    Ok(()) => drop(body),
                    Err((resource, original)) => {
                        actual.partial.slots[i] = ActualInputSlotV1::Owned(RetainedIdentityFileV1 { role,resource,initial,body,sha256 });
                        store_failure_v1(&mut actual.partial, original); return AcquisitionRetirementOutcomeV1::Retained(owner);
                    }
                }
            }
        }
        // Cleanup separately pays each native+retained backing, claims/errors
        // and final carrier. No acquisition ticket or child refund is borrowed.
        for i in 0..10 {
            if owner.reservation.cleanup_v1().is_err() { return AcquisitionRetirementOutcomeV1::Retained(owner); }
            let place = if i < 5 { &mut actual.partial.paths.native[i] } else { &mut actual.partial.paths.retained[i-5] };
            drop(place.take());
        }
        if owner.reservation.cleanup_v1().is_err() { return AcquisitionRetirementOutcomeV1::Retained(owner); }
        drop(owner.actual.take());
        if owner.reservation.cleanup_v1().is_err() { return AcquisitionRetirementOutcomeV1::Retained(owner); }
        let PrepaidInputOwnerV1 { reservation: paid, actual: None, retirement_started: _ } = owner else { unreachable!() };
        AcquisitionRetirementOutcomeV1::Complete(CompleteAcquisitionRetirementV1 { paid })
    }
    impl CompleteAcquisitionRetirementV1<'_> {
        fn release_v1(self) {
            let old = self.paid.root.usage.get();
            if let Some(storage) = old.storage.checked_sub(self.paid.original_storage) {
                self.paid.root.usage.set(BootstrapUsageV1 { storage, ..old });
            }
        }
    }
    pub(in crate::experimental_swift_reactor) fn retire_admitted_owner_v1(owner: AdmittedImmutableOwnerV1<'_>) {
        // All borrowed views must have ended at this consuming call boundary.
        // Native bridge cannot certify healthy close, so no release is possible.
        match retire_acquired_owner_core_v1(owner.0.owned, &mut NativeInputBridgeV1) {
            AcquisitionRetirementOutcomeV1::Retained(original) => drop(original),
            AcquisitionRetirementOutcomeV1::Complete(token) => token.release_v1(),
        }
    }
    // OWNER_TESTS_INSERTION
}
pub(super) use prepaid_input_owner_v1::{
    AdmittedImmutableOwnerV1, AdmittedLoaderCorrespondenceV1, PrepaidCorrelationAttemptV1,
    BootstrapFailureV1, BootstrapLedgerV1, BorrowedOwnerDataV1, SuppliedLoaderCarrierV1, CorrelatedSelectedProfileV1,
    OriginalCorrelationRefusalV1, OwnedCorrelationOutcomeV1, selected_bootstrap_ledger_v1,
    correlate_admitted_loader_v1, retire_admitted_owner_v1,
};
