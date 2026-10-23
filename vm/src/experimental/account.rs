use super::*;

#[derive(Clone, Copy, Debug, Default)]
pub(super) struct Cursor {
    pub function: Option<u32>,
    pub offset: usize,
}
pub(super) struct Meter<'a> {
    budget: ValidationBudget,
    usage: Usage,
    cancellation: &'a Cancellation,
}
impl<'a> Meter<'a> {
    pub fn new(budget: ValidationBudget, cancellation: &'a Cancellation) -> Result<Self, Failure> {
        let defaults = ValidationBudget::default();
        let meter = Self {
            budget,
            usage: Usage::default(),
            cancellation,
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
        if self.cancellation.is_cancelled() {
            Err(self.error(FailureKind::Cancelled, "cancelled", cursor))
        } else {
            Ok(())
        }
    }
    pub fn work(&mut self, credits: u64, cursor: Cursor) -> Result<(), Failure> {
        self.check(cursor)?;
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
    pub fn reserve(
        &mut self,
        category: Resource,
        bytes: usize,
        cursor: Cursor,
    ) -> Result<(), Failure> {
        self.check(cursor)?;
        let (current, limit) = match category {
            Resource::Source => (self.usage.source_bytes, 4 * 1024 * 1024),
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
        meter: &mut Meter<'_>,
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
        if next.try_reserve_exact(capacity).is_err() {
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
        let old = std::mem::replace(&mut self.values, next);
        drop(old);
        meter.release(self.category, self.charged);
        self.charged = bytes;
        Ok(())
    }
    pub fn push(&mut self, value: T, meter: &mut Meter<'_>, cursor: Cursor) -> Result<(), Failure> {
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
    pub fn dispose(self, meter: &mut Meter<'_>) {
        let category = self.category;
        let bytes = self.charged;
        drop(self);
        meter.release(category, bytes);
    }
}
