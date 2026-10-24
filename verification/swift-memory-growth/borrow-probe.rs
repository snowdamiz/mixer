use super::*;
pub(crate) struct SwiftGrowthContext<'a> {pub(crate) memory_ticket: &'a mut Option<ReservationTicket>}
impl SwiftReactorInstance {
    pub(crate) fn prepare_growth(
        &mut self,
        cursor: Cursor,
    ) -> Result<(FrameOperationPhase<'_>, SwiftGrowthContext<'_>), SwiftRunFailure> {
        let Self {
            control,
            cache,
            wasi,
            state,
            lifecycle,
        } = self;
        let control = control.as_mut().expect("constructed control");
        let cache = cache.as_mut().expect("constructed cache");
        let wasi = wasi.as_mut().expect("constructed WASI");
        let state = state.as_mut().expect("constructed State");
        original_owners(control, cache, wasi, state, cursor)?;
        let live = control.usage(Some(wasi.usage())).live;
        if matches!(lifecycle, Lifecycle::Terminal)
            || !state.frame_cleanup.is_empty()
            || !state.frames.is_empty()
            || !state.controls.is_empty()
            || !state.values.is_empty()
            || cache.usage().active_pins != 0
            || live.values.current != 0
            || live.controls.current != 0
            || live.frames.current != 0
            || live.active_pins.current != 0
        {
            return Err(construction_failure(
                control,
                wasi,
                cursor,
                SwiftRunFailureKind::Invariant,
                "swift_frame_prepare_nonempty",
            ));
        }
        let previous = control
            .usage(Some(wasi.usage()))
            .reservations
            .construction
            .current;
        let admitted = match FRAME_OPERATION_BYTES.and_then(|bytes| previous.checked_add(bytes)) {
            Some(admitted) => admitted,
            None => return Err(layout_failure(control, wasi, cursor)),
        };
        control.enlarge_construction_with_wasi(admitted, cursor, Some(wasi.usage()))?;
        // No fallible boundary exists after admission and before its State record.
        state.frame_cleanup.bound = Some(FrameBound { previous, admitted });
        state.frame_cleanup.disposition = FrameDisposition::Active;
        let SwiftExecutionState {memory,table,globals,values,controls,frames,buffers,frame_cleanup,..}=state;
        Ok((FrameOperationPhase {
            phase: ExecutionOperationPhase {
                parts: ExecutionParts {
                    cache,
                    memory,
                    table,
                    globals,
                    values,
                    controls,
                    frames,
                },
                operation: SwiftExecutionOperation {
                    control,
                    wasi,
                    cursor,
                },
                previous_bound: previous,
            },
            cleanup: frame_cleanup,
            lifecycle,
        }, SwiftGrowthContext {memory_ticket: &mut buffers[3]}))
    }
}
