
#[allow(dead_code)]
fn actual_sibling_control_signatures() {
    let _: fn(&mut super::frame_operations::FrameOperationPhase<'static>, Operation, Option<u32>) -> Result<bool, SwiftRunFailure> = super::frame_operations::FrameOperationPhase::control_operation;
    let _: fn(crate::experimental::cache::ControlKind, usize, usize, usize, bool) -> Control = Control::decoded;
    let _: fn(Control) -> bool = Control::result;
    let _: fn(Control) -> usize = Control::height;
    let _: fn(Control) -> usize = Control::start;
    let _: fn(Control) -> usize = Control::end;
    let _: fn(Control) -> bool = Control::is_loop;
    let _: fn(Control) -> bool = Control::is_function;
    let _: fn(Control) -> bool = Control::is_if;
    let _: fn(&mut Control) = Control::clear_result;
}
