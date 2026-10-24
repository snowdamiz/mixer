
fn rejected_original_private_access(mut control: Control) {
    let _ = crate::experimental::execution::Kind::Function;
    let _ = control.kind;
    control.start = 0;
    control.end = 0;
    control.height = 0;
    control.result = false;
}
