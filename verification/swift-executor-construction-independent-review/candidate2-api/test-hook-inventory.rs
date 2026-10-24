// Unit-only engine-side hook call boundaries. Callback storage/Cell bodies are
// test harness instrumentation and are excluded, not production authority.
#[cfg(test)]
#[allow(dead_code)]
struct ConstructionPositiveTestHookArguments {
 checkpoint_reborrow: &'static RuntimeControl,
 checkpoint_argument: &'static RuntimeControl,
 checkpoint_callback_parameter: &'static RuntimeControl,
 checkpoint_cursor_argument: Cursor,
 checkpoint_cursor_callback_parameter: Cursor,
 checkpoint_call_return: (),
 checkpoint_callback_return: (),
 capacity_new_source: usize,
 capacity_argument: usize,
 capacity_callback_parameter: usize,
 capacity_callback_return: usize,
 restore_new_source: usize,
 restore_argument: usize,
 restore_callback_parameter: usize,
 restore_callback_return: usize,
}
#[cfg(test)]
pub(super) const CONSTRUCTION_POSITIVE_TEST_HOOK_BYTES:usize=std::mem::size_of::<ConstructionPositiveTestHookArguments>();
#[cfg(not(test))]
pub(super) const CONSTRUCTION_POSITIVE_TEST_HOOK_BYTES:usize=0;

