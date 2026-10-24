// Derived only from the actual accepted literal macro; never run here.
#[allow(unused_macros)]
macro_rules! contract_control_methods {
    ($this:ident, $failure:ty, $leaf:ident, $control:ident, {$($close_prelude:tt)*}) => {
        fn pop32(&mut $this) -> Result<i32, $failure> {
            match $leaf!(pop $this)? {
                Value::I32(value) => Ok(value),
                _ => Err($leaf!(invariant $this)),
            }
        }
        fn close_control(&mut $this, $control: Control) -> Result<(), $failure> {
            $($close_prelude)*
            let value = if $leaf!(result $control) {
                Some($leaf!(pop $this)?)
            } else {
                None
            };
            if $leaf!(height $control) > $leaf!(values $this).len() {
                return Err($leaf!(invariant $this));
            }
            $this.work($leaf!(values $this).len() - $leaf!(height $control) + 1)?;
            $leaf!(truncate_values $this, $leaf!(height $control));
            $leaf!(observe $this);
            if let Some(value) = value {
                $leaf!(push $this, value)?;
            }
            Ok(())
        }
        fn branch(&mut $this, depth: u32) -> Result<bool, $failure> {
            $leaf!(frame $this, frame);
            let index = $leaf!(controls $this)
                .len()
                .checked_sub(depth as usize + 1)
                .filter(|i| *i >= $leaf!(floor frame))
                .ok_or_else(|| $leaf!(invariant $this))?;
            let mut $control = $leaf!(controls $this)[index];
            $this.work($leaf!(controls $this).len() - index)?;
            if $leaf!(loop $control) {
                $leaf!(clear $control);
            }
            $this.close_control($control)?;
            $leaf!(truncate_controls $this, if $leaf!(loop $control) {
                index + 1
            } else {
                index
            });
            let pc = if $leaf!(loop $control) {
                $leaf!(start $control)
            } else {
                $leaf!(after_end $control)
            };
            $leaf!(set_pc $this, pc);
            $leaf!(observe $this);
            Ok($leaf!(function $control))
        }
    };
}
pub(crate) use contract_control_methods;
