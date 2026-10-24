//! Private original-owner memory.grow. No public or full-dispatch route.
#![allow(dead_code, clippy::result_large_err, clippy::large_enum_variant, clippy::type_complexity)]
use super::*;
use crate::experimental::execution::CHUNK;

pub(crate) struct SwiftGrowthContext<'a> {
    pub(crate) memory_ticket: &'a mut Option<ReservationTicket>,
}
/// Caller-owned real transfer state, retained with the admitted frame envelope.
/// `pages_debited` is only uncommitted new live-page authority.
pub(crate) struct SwiftGrowthStorage {
    pub(crate) transfer: GrowthTransfer,
    pub(crate) pages_debited: usize,
    pub(crate) live_unreconciled: bool,
}
impl SwiftGrowthStorage {
    pub(crate) fn empty() -> Self {
        Self {
            transfer: GrowthTransfer {replacement:Vec::new(),ticket:None,old:Vec::new(),old_ticket:None,old_pages:0,next_pages:0,copied:0},
            pages_debited:0,
            live_unreconciled:false,
        }
    }
    fn vacant(&self) -> bool {
        self.transfer.replacement.capacity()==0 && self.transfer.old.capacity()==0
            && self.transfer.ticket.is_none() && self.transfer.old_ticket.is_none()
            && self.pages_debited==0 && !self.live_unreconciled
    }
}
struct SwiftGrowthExecution<'short,'owner> {
    phase: &'short mut FrameOperationPhase<'owner>,
    context: &'short mut SwiftGrowthContext<'owner>,
    storage: &'short mut SwiftGrowthStorage,
}
macro_rules! swift_growth_leaf {
    (work $s:ident,$amount:expr $(,)?) => {{let credits=$amount;$s.phase.work(credits)}};
    (pop32 $s:ident) => {$s.phase.memory_pop32()};
    (pages $s:ident) => {$s.phase.phase.operation.control.usage(Some($s.phase.phase.operation.wasi.usage())).live.memory_pages.current as u32};
    (maximum $s:ident) => {$s.maximum()?};
    (push $s:ident, $value:expr) => {$s.phase.memory_push_value($value)};
    (invariant $s:ident) => {$s.invariant()};
    (memory $s:ident) => {$s.phase.phase.parts.memory};
    (allocation $s:ident, $bytes:expr) => {$s.allocate($bytes)};
    (check $s:ident) => {$s.check()};
    (zero_check $s:ident,$memory:ident) => {$s.checked_memory(&$memory,1)};
    (copy_check $s:ident,$memory:ident) => {$s.checked_memory(&$memory,2)};
    (final_check $s:ident,$memory:ident) => {$s.checked_memory(&$memory,3)};
    (rollback $s:ident, $memory:ident, $bytes:ident) => {drop($memory);$s.release_pending()?;};
    (commit $s:ident, $memory:ident, $old_bytes:ident, $next:ident) => {$s.commit($memory,$old_bytes,$next)?;};
}
impl SwiftGrowthExecution<'_,'_> {
    crate::experimental::execution::borrowed::shared_memory_growth!(self,SwiftRunFailure,swift_growth_leaf,grow);
    fn invariant(&mut self) -> SwiftRunFailure {self.phase.invariant("swift_growth_arithmetic")}
    fn work(&mut self, amount:usize) -> Result<(),SwiftRunFailure> {self.phase.work(amount)}
    fn maximum(&mut self) -> Result<u32,SwiftRunFailure> {
        let descriptor=self.phase.phase.parts.cache.proof().execution_memory().ok_or_else(||self.phase.invariant("swift_growth_memory_missing"))?;
        Ok(descriptor.declared_maximum.unwrap_or(descriptor.host_maximum)
            .min(descriptor.host_maximum).min(self.phase.phase.operation.control.budget().memory_pages))
    }
    fn check(&mut self) -> Result<(),SwiftRunFailure> {
        #[cfg(test)] tests::growth_checkpoint(self.phase.phase.operation.control);
        self.phase.phase.operation.control.check_with_wasi(self.phase.phase.operation.cursor,Some(self.phase.phase.operation.wasi.usage()))
    }
    fn checked_memory(&mut self, memory:&[u8], stage:u8) -> Result<(),SwiftRunFailure> {
        #[cfg(test)] tests::observe_memory(self.phase,memory,stage);
        #[cfg(not(test))] let _=(memory,stage);
        self.check()
    }
    fn allocate(&mut self, bytes:usize) -> Result<Vec<u8>,SwiftRunFailure> {
        self.storage.transfer.old_pages=(self.phase.phase.parts.memory.len()/PAGE)as u32;
        self.storage.transfer.next_pages=(bytes/PAGE)as u32;
        let ticket=self.phase.phase.operation.control.admit_with_wasi(SwiftReservationCategory::State,bytes,self.phase.phase.operation.cursor,Some(self.phase.phase.operation.wasi.usage()))?;
        self.storage.transfer.ticket=Some(ticket);
        let delta=(self.storage.transfer.next_pages-self.storage.transfer.old_pages)as usize;
        let result=(|| {
            self.phase.phase.operation.control.add_live_with_wasi(Live::MemoryPages,delta,self.phase.phase.operation.cursor,Some(self.phase.phase.operation.wasi.usage()))?;
            self.storage.pages_debited=delta;
            self.check()?;
            self.storage.transfer.replacement.try_reserve_exact(bytes).map_err(|_| {
                let mut fault=Fault::new(SwiftRunFailureKind::Allocation,"swift_growth_allocation");fault.attempted=bytes as u64;
                self.phase.phase.operation.control.fail(self.phase.phase.operation.cursor,fault,Some(self.phase.phase.operation.wasi.usage()))
            })?;
            #[cfg(test)] let observed=tests::capacity(self.storage.transfer.replacement.capacity());
            #[cfg(not(test))] let observed=self.storage.transfer.replacement.capacity();
            self.phase.phase.operation.control.exact_capacity_with_wasi(bytes,observed,self.phase.phase.operation.cursor,Some(self.phase.phase.operation.wasi.usage()))?;
            self.check()?;
            Ok(())
        })();
        if let Err(error)=result {drop(take(&mut self.storage.transfer.replacement));let _=self.release_pending();return Err(error);}
        Ok(take(&mut self.storage.transfer.replacement))
    }
    fn release_ticket(&mut self, old:bool) -> Result<(),SwiftRunFailure> {
        let transfer=&mut self.storage.transfer;
        let (slot,pages)=if old {(&mut transfer.old_ticket,transfer.old_pages)}else{(&mut transfer.ticket,transfer.next_pages)};
        if let Some(ticket)=slot.as_ref() {
            if !ticket.matches_layout(SwiftReservationCategory::State,(pages as usize)*PAGE) {
                return Err(self.phase.invariant("swift_growth_ticket_layout"));
            }
        }
        if let Some(ticket)=slot.as_ref() {
            let control=&mut *self.phase.phase.operation.control;
            let wasi=Some(self.phase.phase.operation.wasi.usage());
            control.check_reservation_owner(ticket,self.phase.phase.operation.cursor,wasi)?;
            // Same exclusive control borrow; () has no destructor or callback.
            // The borrowed check proves every subtraction and owner predicate
            // in refund_with_wasi, with exact original layout checked above.
            let ticket=slot.take().expect("validated original growth ticket");
            control.drop_reserved_with_wasi((),ticket,wasi)
        } else {Ok(())}
    }
    fn release_pending(&mut self) -> Result<(),SwiftRunFailure> {
        drop(take(&mut self.storage.transfer.replacement));drop(take(&mut self.storage.transfer.old));
        if self.storage.live_unreconciled {return Err(self.phase.invariant("swift_growth_live_debt"));}
        if self.storage.pages_debited!=0 {
            let result=self.phase.phase.operation.control.remove_live_with_wasi(Live::MemoryPages,self.storage.pages_debited,Some(self.phase.phase.operation.wasi.usage()));
            if let Err(error)=result {self.storage.live_unreconciled=true;return Err(error);}
            self.storage.pages_debited=0;
        }
        self.release_ticket(false)?;
        self.release_ticket(true)
    }
    fn commit(&mut self, memory:Vec<u8>, old_bytes:usize, next:u32) -> Result<(),SwiftRunFailure> {
        // Every fallible preflight occurs before authority or original storage moves.
        if self.storage.transfer.ticket.is_none() || self.context.memory_ticket.is_none()
            || self.storage.transfer.old_ticket.is_some() || self.storage.transfer.old.capacity()!=0
            || self.storage.pages_debited!=(next-self.storage.transfer.old_pages)as usize
            || old_bytes!=self.phase.phase.parts.memory.len() {
            drop(memory);let failure=self.phase.invariant("swift_growth_commit_state");let _=self.release_pending();return Err(failure);
        }
        self.storage.transfer.replacement=memory;
        self.storage.transfer.old=std::mem::replace(self.phase.phase.parts.memory,take(&mut self.storage.transfer.replacement));
        self.storage.transfer.old_ticket=self.context.memory_ticket.take();
        *self.context.memory_ticket=self.storage.transfer.ticket.take();
        // The admitted positive delta now belongs to the actual committed State.
        self.storage.pages_debited=0;
        drop(take(&mut self.storage.transfer.old));
        #[cfg(test)] tests::before_old_refund(self.phase,self.storage);
        self.release_ticket(true)
    }
    fn preflight(&mut self) -> Result<(),SwiftRunFailure> {
        if !self.storage.vacant() {return Err(self.phase.invariant("swift_growth_pending_storage"));}
        let length=self.phase.phase.parts.memory.len();
        let pages=self.phase.phase.operation.control.usage(Some(self.phase.phase.operation.wasi.usage())).live.memory_pages.current;
        if !length.is_multiple_of(PAGE) || length!=self.phase.phase.parts.memory.capacity() || pages!=length/PAGE {
            return Err(self.phase.invariant("swift_growth_page_agreement"));
        }
        let ticket=self.context.memory_ticket.as_ref().ok_or_else(||self.phase.invariant("swift_growth_ticket_missing"))?;
        self.phase.phase.operation.control.check_reservation_owner(ticket,self.phase.phase.operation.cursor,Some(self.phase.phase.operation.wasi.usage()))?;
        if !ticket.matches_layout(SwiftReservationCategory::State,length) {return Err(self.phase.invariant("swift_growth_ticket_layout"));}
        let frame=match self.phase.phase.parts.frames.last(){Some(frame)=>frame,None=>return Err(self.phase.invariant("swift_growth_frame_missing"))};
        if frame.base>frame.operands || frame.controls>self.phase.phase.parts.controls.len() {return Err(self.phase.invariant("swift_growth_frame_floor"));}
        let available=self.phase.phase.parts.values.len().checked_sub(frame.operands).ok_or_else(||self.phase.invariant("swift_growth_operand_floor"))?;
        if available<1 {return Err(self.phase.invariant("swift_growth_operand_count"));}
        if self.phase.phase.parts.values.last().map(|value|value.ty())!=Some(crate::Type::I32) {return Err(self.phase.invariant("swift_growth_operand_type"));}
        Ok(())
    }
}

pub(crate) fn growth_operation<'a>(phase:&mut FrameOperationPhase<'a>,context:&mut SwiftGrowthContext<'a>,growth:&mut SwiftGrowthStorage,operation:Operation,returned:&mut Option<Result<(),SwiftRunFailure>>) -> Result<(),SwiftRunFailure> {
    if returned.is_some() {let failure=phase.invariant("swift_growth_result_occupied");phase.terminal();return Err(failure);}
    let result=growth_operation_inner(phase,context,growth,operation);
    if result.is_err(){phase.terminal();}
    *returned=Some(result);Ok(())
}
fn growth_unsupported(phase:&mut FrameOperationPhase<'_>) -> SwiftRunFailure {phase.phase.operation.control.fail(phase.phase.operation.cursor,Fault::new(SwiftRunFailureKind::UnsupportedEnvironment,"swift_growth_unsupported_operation"),Some(phase.phase.operation.wasi.usage()))}
fn growth_operation_inner<'a>(phase:&mut FrameOperationPhase<'a>,context:&mut SwiftGrowthContext<'a>,growth:&mut SwiftGrowthStorage,operation:Operation) -> Result<(),SwiftRunFailure> {
    phase.active()?;
    if !matches!(operation,Operation::MemoryGrow) {return Err(growth_unsupported(phase));}
    let mut execution=SwiftGrowthExecution{phase,context,storage:growth};execution.preflight()?;execution.grow()
}
pub(crate) fn growth_pinned_caller<'a>(phase:&mut FrameOperationPhase<'a>,context:&mut SwiftGrowthContext<'a>,growth:&mut SwiftGrowthStorage,storage:&mut FrameOperationStorage<'a>) -> Result<(),SwiftRunFailure> {
    if storage.entry.is_some(){let failure=phase.invariant("swift_growth_result_occupied");phase.terminal();return Err(failure);}
    let result=growth_pinned_step(phase,context,growth);if result.is_err(){phase.terminal();}storage.entry=Some(result);Ok(())
}
fn growth_pinned_step<'a>(phase:&mut FrameOperationPhase<'a>,context:&mut SwiftGrowthContext<'a>,growth:&mut SwiftGrowthStorage) -> Result<(),SwiftRunFailure> {
    phase.active()?;
    let selected={
        let frame=match phase.phase.parts.frames.last(){Some(frame)=>frame,None=>return Err(phase.invariant("swift_growth_caller_frame"))};
        let view=phase.phase.parts.cache.view(&frame.pin,phase.phase.operation.control,Some(&*phase.phase.operation.wasi))?;
        let instruction=match view.instructions.get(frame.pc){Some(instruction)=>*instruction,None=>return Err(phase.invariant("swift_growth_caller_instruction"))};
        (frame.function,instruction)
    };
    let(function,instruction)=selected;
    phase.phase.operation.cursor=Cursor{stage:SwiftRunStage::Invocation,function:Some(function),offset:Some(instruction.offset)};
    if !matches!(instruction.operation,Operation::MemoryGrow){return Err(growth_unsupported(phase));}
    phase.phase.operation.control.instruction_with_wasi(phase.phase.operation.cursor,Some(phase.phase.operation.wasi.usage()))?;
    phase.work(1)?;
    #[cfg(test)] if tests::PC_OVERFLOW.with(std::cell::Cell::get){phase.phase.parts.frames.last_mut().expect("actual frame").pc=usize::MAX;}
    let pc=phase.phase.parts.frames.last().and_then(|frame|frame.pc.checked_add(1)).ok_or_else(||phase.invariant("swift_growth_caller_pc"))?;
    phase.phase.parts.frames.last_mut().expect("actual frame").pc=pc;
    growth_operation_inner(phase,context,growth,instruction.operation)
}
pub(crate) fn release_growth_pending<'a>(phase:&mut FrameOperationPhase<'a>,context:&mut SwiftGrowthContext<'a>,growth:&mut SwiftGrowthStorage) -> Result<(),SwiftRunFailure> {
    SwiftGrowthExecution{phase,context,storage:growth}.release_pending()
}
/// Retained variant owns the exact phase, ticket borrow, transfer and caller
/// wrappers; dropping it cannot refund their original admitted envelope.
#[must_use="Retained growth authority requires explicit cleanup retry"]
pub(crate) enum GrowthCompletion<'a> {
    Completed(FrameCompletion),
    Retained {
        phase:FrameOperationPhase<'a>,
        context:SwiftGrowthContext<'a>,
        growth:SwiftGrowthStorage,
        storage:FrameOperationStorage<'a>,
        preparation:Option<Result<(FrameOperationPhase<'a>,SwiftGrowthContext<'a>),SwiftRunFailure>>,
    },
}
pub(crate) fn complete_growth<'a>(mut phase:FrameOperationPhase<'a>,context:SwiftGrowthContext<'a>,growth:SwiftGrowthStorage,storage:FrameOperationStorage<'a>,preparation:Option<Result<(FrameOperationPhase<'a>,SwiftGrowthContext<'a>),SwiftRunFailure>>) -> GrowthCompletion<'a> {
    if !growth.vacant() || preparation.is_some() {
        phase.terminal();
        return GrowthCompletion::Retained{phase,context,growth,storage,preparation};
    }
    // Explicitly destroy every growth/preparation wrapper while the original
    // frame envelope still covers it; then use original fixed completion.
    drop((context,growth,preparation));
    GrowthCompletion::Completed(phase.complete(storage))
}

#[cfg(test)] #[path="memory_growth_operations_tests.rs"] mod tests;
// ACCOUNTING_START
struct PermanentPositions {}
struct ActivePositions {}
pub(in crate::experimental_swift_reactor::execution) const PERMANENT_BYTES:usize=size_of::<PermanentPositions>();
pub(super) const ACTIVE_BYTES:usize=size_of::<ActivePositions>();
