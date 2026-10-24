// Proposed overlay only. This file is not included by product source.
#[cfg(feature = "experimental-span-execution")]
macro_rules! frozen_control_methods {
    () => {
        fn pop32(&mut self) -> Result<i32, ExecutionFailure> {
            match self.pop()? {
                Value::I32(value) => Ok(value),
                _ => Err(self.invariant()),
            }
        }
        fn close_control(&mut self, control: Control) -> Result<(), ExecutionFailure> {
            let value = if control.result {
                Some(self.pop()?)
            } else {
                None
            };
            if control.height > self.values.len() {
                return Err(self.invariant());
            }
            self.work(self.values.len() - control.height + 1)?;
            self.values.truncate(control.height);
            self.observe();
            if let Some(value) = value {
                self.push(value)?;
            }
            Ok(())
        }
        fn branch(&mut self, depth: u32) -> Result<bool, ExecutionFailure> {
            let frame = self.frames.last().ok_or_else(|| self.invariant())?;
            let index = self
                .controls
                .len()
                .checked_sub(depth as usize + 1)
                .filter(|i| *i >= frame.controls)
                .ok_or_else(|| self.invariant())?;
            let mut control = self.controls[index];
            self.work(self.controls.len() - index)?;
            if control.kind == Kind::Loop {
                control.result = false;
            }
            self.close_control(control)?;
            self.controls.truncate(if control.kind == Kind::Loop {
                index + 1
            } else {
                index
            });
            let pc = if control.kind == Kind::Loop {
                control.start
            } else {
                control.end + 1
            };
            self.frames.last_mut().ok_or_else(unreachable_failure)?.pc = pc;
            self.observe();
            Ok(control.kind == Kind::Function)
        }
    };
}

#[cfg(feature = "experimental-span-execution")]
pub(super) use frozen_control_methods;
