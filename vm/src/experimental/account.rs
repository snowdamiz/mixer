use super::*;

#[derive(Clone, Copy, Debug, Default)]
pub(super) struct Cursor {
    pub function: Option<u32>,
    pub offset: usize,
}
pub(super) trait MeterControl {
    const SAMPLE_WORK_CLOCK: bool = false;

    fn source_limit(&self) -> usize {
        4 * 1024 * 1024
    }
    fn expired(&self) -> bool {
        false
    }
    fn operand(&mut self, _: usize) {}
    fn control(&mut self, _: usize) {}
    fn locals(&mut self, _: usize) {}
    fn body(&mut self) {}
}
// This zero-sized specialization preserves frozen Meter layout and semantics,
// including in binaries that also enable the Swift experiment.
pub(super) struct FrozenControl;
impl MeterControl for FrozenControl {}
#[cfg(feature = "experimental-swift-reactor")]
#[derive(Clone, Copy, Default)]
pub(super) struct BodyObservations {
    pub validated_bodies: usize,
    pub max_parameters_plus_locals: usize,
    pub max_operand_values: usize,
    pub max_control_depth: usize,
}
#[cfg(feature = "experimental-swift-reactor")]
pub(super) struct SwiftControl<const SAMPLE_WORK_CLOCK: bool = false> {
    source_limit: usize,
    deadline: std::time::Instant,
    pub observations: BodyObservations,
}
#[cfg(feature = "experimental-swift-reactor")]
impl<const SAMPLE_WORK_CLOCK: bool> MeterControl for SwiftControl<SAMPLE_WORK_CLOCK> {
    const SAMPLE_WORK_CLOCK: bool = SAMPLE_WORK_CLOCK;

    fn source_limit(&self) -> usize {
        self.source_limit
    }
    fn expired(&self) -> bool {
        std::time::Instant::now() >= self.deadline
    }
    fn operand(&mut self, n: usize) {
        self.observations.max_operand_values = self.observations.max_operand_values.max(n);
    }
    fn control(&mut self, n: usize) {
        self.observations.max_control_depth = self.observations.max_control_depth.max(n);
    }
    fn locals(&mut self, n: usize) {
        self.observations.max_parameters_plus_locals =
            self.observations.max_parameters_plus_locals.max(n);
    }
    fn body(&mut self) {
        self.observations.validated_bodies += 1;
    }
}
pub(super) struct Meter<'a, C: MeterControl = FrozenControl> {
    budget: ValidationBudget,
    usage: Usage,
    cancellation: &'a Cancellation,
    pub control: C,
}
impl<'a> Meter<'a> {
    pub fn new(budget: ValidationBudget, cancellation: &'a Cancellation) -> Result<Self, Failure> {
        let defaults = ValidationBudget::default();
        let meter = Self {
            budget,
            usage: Usage::default(),
            cancellation,
            control: FrozenControl,
        };
        if budget.metadata_bytes > defaults.metadata_bytes
            || budget.scratch_bytes > defaults.scratch_bytes
            || budget.work_credits > defaults.work_credits
        {
            return Err(meter.error(
                FailureKind::InvalidBudget,
                "invalid_validation_budget",
                Cursor::default(),
            ));
        }
        Ok(meter)
    }
}
#[cfg(feature = "experimental-swift-reactor")]
impl<'a> Meter<'a, SwiftControl> {
    pub fn swift(
        budget: ValidationBudget,
        source_limit: usize,
        cancellation: &'a Cancellation,
        deadline: std::time::Instant,
    ) -> Self {
        Self {
            budget,
            usage: Usage::default(),
            cancellation,
            control: SwiftControl {
                source_limit,
                deadline,
                observations: BodyObservations::default(),
            },
        }
    }

    pub fn for_bodies<const SAMPLE_WORK_CLOCK: bool>(
        self,
    ) -> Meter<'a, SwiftControl<SAMPLE_WORK_CLOCK>> {
        Meter {
            budget: self.budget,
            usage: self.usage,
            cancellation: self.cancellation,
            control: SwiftControl {
                source_limit: self.control.source_limit,
                deadline: self.control.deadline,
                observations: self.control.observations,
            },
        }
    }
}
impl<C: MeterControl> Meter<'_, C> {
    pub fn source_limit(&self) -> usize {
        self.control.source_limit()
    }
    pub fn usage(&self) -> Usage {
        self.usage
    }
    pub fn error(&self, kind: FailureKind, code: &'static str, cursor: Cursor) -> Failure {
        Failure {
            kind,
            code,
            function: cursor.function,
            offset: cursor.offset,
            resource: None,
            attempted: 0,
            limit: 0,
            usage: self.usage,
        }
    }
    pub fn check(&self, cursor: Cursor) -> Result<(), Failure> {
        self.check_cancellation(cursor)?;
        if self.control.expired() {
            return Err(self.error(FailureKind::Cancelled, "swift_deadline", cursor));
        }
        Ok(())
    }
    fn check_cancellation(&self, cursor: Cursor) -> Result<(), Failure> {
        if self.cancellation.is_cancelled() {
            Err(self.error(FailureKind::Cancelled, "cancelled", cursor))
        } else {
            Ok(())
        }
    }
    pub fn work(&mut self, credits: u64, cursor: Cursor) -> Result<(), Failure> {
        // Only body validation uses this mode. Body work sites charge at most
        // eight credits per operation, so successive interval checks span at
        // most 128 + 7 credits. Cancellation is checked at every work site.
        const CLOCK_INTERVAL_CREDITS: u64 = 128;
        if C::SAMPLE_WORK_CLOCK
            && credits < CLOCK_INTERVAL_CREDITS - self.usage.work_used % CLOCK_INTERVAL_CREDITS
        {
            self.check_cancellation(cursor)?;
        } else {
            self.check(cursor)?;
        }
        let attempted = self.usage.work_used.checked_add(credits).ok_or_else(|| {
            self.error(FailureKind::ResourceExhausted, "validation_work", cursor)
                .resource(Resource::Work, u64::MAX, self.budget.work_credits)
        })?;
        if attempted > self.budget.work_credits {
            return Err(self
                .error(FailureKind::ResourceExhausted, "validation_work", cursor)
                .resource(Resource::Work, attempted, self.budget.work_credits));
        }
        self.usage.work_used = attempted;
        Ok(())
    }
    pub fn body_boundary(&self, cursor: Cursor) -> Result<(), Failure> {
        if C::SAMPLE_WORK_CLOCK {
            self.check(cursor)?;
        }
        Ok(())
    }
    #[cfg(feature = "experimental-swift-reactor")]
    pub fn body_failure(&self, error: Failure) -> Failure {
        if C::SAMPLE_WORK_CLOCK && error.kind != FailureKind::Cancelled {
            let cursor = Cursor {
                function: error.function,
                offset: error.offset,
            };
            if let Err(mut stopped) = self.check(cursor) {
                stopped.usage = error.usage;
                return stopped;
            }
        }
        error
    }
    pub fn reserve(
        &mut self,
        category: Resource,
        bytes: usize,
        cursor: Cursor,
    ) -> Result<(), Failure> {
        self.check(cursor)?;
        let (current, limit) = match category {
            Resource::Source => (self.usage.source_bytes, self.source_limit()),
            Resource::Metadata => (self.usage.metadata_reserved, self.budget.metadata_bytes),
            Resource::Scratch => (self.usage.scratch_reserved, self.budget.scratch_bytes),
            Resource::Work | Resource::Profile => unreachable!(),
        };
        let attempted = current.checked_add(bytes).ok_or_else(|| {
            self.error(
                FailureKind::ResourceExhausted,
                "validation_capacity",
                cursor,
            )
            .resource(category, u64::MAX, limit as u64)
        })?;
        if attempted > limit {
            return Err(self
                .error(
                    FailureKind::ResourceExhausted,
                    "validation_capacity",
                    cursor,
                )
                .resource(category, attempted as u64, limit as u64));
        }
        match category {
            Resource::Source => self.usage.source_bytes = attempted,
            Resource::Metadata => {
                self.usage.metadata_reserved = attempted;
                self.usage.metadata_peak_reserved =
                    self.usage.metadata_peak_reserved.max(attempted);
            }
            Resource::Scratch => {
                self.usage.scratch_reserved = attempted;
                self.usage.scratch_peak_reserved = self.usage.scratch_peak_reserved.max(attempted);
            }
            Resource::Work | Resource::Profile => unreachable!(),
        }
        let total = self
            .usage
            .source_bytes
            .checked_add(self.usage.metadata_reserved)
            .and_then(|n| n.checked_add(self.usage.scratch_reserved))
            .ok_or_else(|| {
                self.error(FailureKind::ResourceExhausted, "capacity_overflow", cursor)
            })?;
        self.usage.total_peak_reserved = self.usage.total_peak_reserved.max(total);
        Ok(())
    }
    pub fn release(&mut self, category: Resource, bytes: usize) {
        match category {
            Resource::Source => self.usage.source_bytes -= bytes,
            Resource::Metadata => self.usage.metadata_reserved -= bytes,
            Resource::Scratch => self.usage.scratch_reserved -= bytes,
            Resource::Work | Resource::Profile => unreachable!(),
        }
    }
}

/// Every growth reserves old + new requested capacity before allocation, and
/// releases old capacity only after its payload is actually dropped.
pub(super) struct Buffer<T: Copy> {
    values: Vec<T>,
    charged: usize,
    category: Resource,
}
impl<T: Copy> Buffer<T> {
    pub fn new(category: Resource) -> Self {
        Self {
            values: Vec::new(),
            charged: 0,
            category,
        }
    }
    pub fn len(&self) -> usize {
        self.values.len()
    }
    pub fn as_slice(&self) -> &[T] {
        &self.values
    }
    pub fn get(&self, index: usize) -> Option<&T> {
        self.values.get(index)
    }
    pub fn get_mut(&mut self, index: usize) -> Option<&mut T> {
        self.values.get_mut(index)
    }
    pub fn last(&self) -> Option<&T> {
        self.values.last()
    }
    pub fn last_mut(&mut self) -> Option<&mut T> {
        self.values.last_mut()
    }
    pub fn pop(&mut self) -> Option<T> {
        self.values.pop()
    }
    pub fn truncate(&mut self, len: usize) {
        self.values.truncate(len)
    }
    pub fn swap(&mut self, a: usize, b: usize) {
        self.values.swap(a, b)
    }
    pub fn reserve(
        &mut self,
        capacity: usize,
        meter: &mut Meter<'_, impl MeterControl>,
        cursor: Cursor,
    ) -> Result<(), Failure> {
        if capacity <= self.values.capacity() {
            return Ok(());
        }
        let bytes = capacity
            .checked_mul(std::mem::size_of::<T>())
            .ok_or_else(|| {
                meter.error(FailureKind::ResourceExhausted, "capacity_overflow", cursor)
            })?;
        meter.reserve(self.category, bytes, cursor)?;
        let mut next = Vec::new();
        let allocation = next.try_reserve_exact(capacity);
        if let Err(error) = meter.body_boundary(cursor) {
            drop(next);
            meter.release(self.category, bytes);
            return Err(error);
        }
        if allocation.is_err() {
            meter.release(self.category, bytes);
            return Err(meter.error(FailureKind::AllocationFailure, "vector_allocation", cursor));
        }
        if next.capacity() != capacity {
            drop(next);
            meter.release(self.category, bytes);
            return Err(meter.error(FailureKind::AllocationFailure, "vector_capacity", cursor));
        }
        // Fallible copying leaves old storage intact until the new buffer is complete.
        for item in &self.values {
            if let Err(error) = meter.work(1, cursor) {
                drop(next);
                meter.release(self.category, bytes);
                return Err(error);
            }
            next.push(*item);
        }
        if let Err(error) = meter.body_boundary(cursor) {
            drop(next);
            meter.release(self.category, bytes);
            return Err(error);
        }
        let old = std::mem::replace(&mut self.values, next);
        drop(old);
        meter.release(self.category, self.charged);
        self.charged = bytes;
        Ok(())
    }
    pub fn push(
        &mut self,
        value: T,
        meter: &mut Meter<'_, impl MeterControl>,
        cursor: Cursor,
    ) -> Result<(), Failure> {
        meter.work(1, cursor)?;
        if self.values.len() == self.values.capacity() {
            let initial = if std::mem::size_of::<T>() == 1 { 8 } else { 4 };
            let capacity = self
                .values
                .capacity()
                .checked_mul(2)
                .map(|n| n.max(initial))
                .ok_or_else(|| {
                    meter.error(FailureKind::ResourceExhausted, "capacity_overflow", cursor)
                })?;
            self.reserve(capacity, meter, cursor)?;
        }
        self.values.push(value);
        Ok(())
    }
    pub fn dispose(self, meter: &mut Meter<'_, impl MeterControl>) {
        let category = self.category;
        let bytes = self.charged;
        drop(self);
        meter.release(category, bytes);
    }
}

#[cfg(all(test, feature = "experimental-swift-reactor"))]
mod tests {
    use super::*;
    use std::cell::Cell;

    #[derive(Default)]
    struct TestClock {
        now: Cell<u64>,
        last_sample: Cell<u64>,
        expired: Cell<bool>,
    }

    impl MeterControl for TestClock {
        const SAMPLE_WORK_CLOCK: bool = true;

        fn expired(&self) -> bool {
            self.last_sample.set(self.now.get());
            self.expired.get()
        }
    }

    fn sampled_meter(cancellation: &Cancellation) -> Meter<'_, TestClock> {
        Meter {
            budget: ValidationBudget::default(),
            usage: Usage::default(),
            cancellation,
            control: TestClock::default(),
        }
    }

    #[test]
    fn sampled_body_clock_bounds_charged_work_across_multi_credit_operations() {
        let cancellation = Cancellation::default();
        let cursor = Cursor::default();
        for initial in 0..128 {
            let mut meter = sampled_meter(&cancellation);
            meter.usage.work_used = initial;
            meter.control.now.set(initial);
            meter.body_boundary(cursor).unwrap();

            // Check just before the 128 boundary, then consume to the end
            // of the following interval one credit at a time.
            for credits in (0..127 - initial)
                .map(|_| 1)
                .chain([8])
                .chain((0..260).map(|_| 1))
            {
                let before = meter.usage.work_used;
                meter.control.now.set(before);
                meter.work(credits, cursor).unwrap();
                assert_eq!(meter.usage.work_used, before + credits);
                assert!(meter.usage.work_used - meter.control.last_sample.get() <= 135);
            }
        }
    }

    #[test]
    fn sampled_body_checks_expiry_at_boundaries_and_preserves_failure_precedence() {
        let cancellation = Cancellation::default();
        let mut meter = sampled_meter(&cancellation);
        let cursor = Cursor {
            function: Some(32),
            offset: 75,
        };
        meter.usage.work_used = 126;
        meter.body_boundary(cursor).unwrap();
        meter.control.expired.set(true);

        meter.work(1, cursor).unwrap();
        assert_eq!(meter.work(1, cursor).unwrap_err().code, "swift_deadline");
        assert_eq!(meter.usage.work_used, 127);
        assert_eq!(meter.body_boundary(cursor).unwrap_err().code, "swift_deadline");
        assert_eq!(
            meter.reserve(Resource::Scratch, 8, cursor).unwrap_err().code,
            "swift_deadline"
        );
        assert_eq!(meter.usage.scratch_reserved, 0);

        let malformed = meter.error(FailureKind::Malformed, "unexpected_end", cursor);
        let expired = meter.body_failure(malformed);
        assert_eq!(
            (expired.code, expired.function, expired.offset),
            ("swift_deadline", Some(32), 75)
        );
        assert_eq!(expired.usage, malformed.usage);

        cancellation.cancel();
        assert_eq!(meter.work(1, cursor).unwrap_err().code, "cancelled");
        assert_eq!(meter.body_failure(malformed).code, "cancelled");
        assert_eq!(meter.body_failure(expired), expired);
        assert_eq!(meter.usage.work_used, 127);
    }
}
