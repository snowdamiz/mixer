use super::*;

pub(super) struct Reader<'a> {
    pub bytes: &'a [u8],
    pub position: usize,
    pub base: usize,
    pub function: Option<u32>,
}
impl<'a> Reader<'a> {
    pub fn new(bytes: &'a [u8], base: usize) -> Self {
        Self {
            bytes,
            position: 0,
            base,
            function: None,
        }
    }
    pub fn cursor(&self) -> Cursor {
        // Reader construction is private: every nested slice comes from a
        // successful take(), so base + position stays inside the policy source.
        Cursor {
            function: self.function,
            offset: self.base + self.position,
        }
    }
    pub fn error(
        &self,
        meter: &Meter<'_, impl MeterControl>,
        kind: FailureKind,
        code: &'static str,
    ) -> Failure {
        meter.error(kind, code, self.cursor())
    }
    pub fn byte(&mut self, meter: &mut Meter<'_, impl MeterControl>) -> Result<u8, Failure> {
        meter.work(1, self.cursor())?;
        let b = *self
            .bytes
            .get(self.position)
            .ok_or_else(|| self.error(meter, FailureKind::Malformed, "unexpected_end"))?;
        self.position += 1;
        Ok(b)
    }
    pub fn take(
        &mut self,
        n: usize,
        meter: &mut Meter<'_, impl MeterControl>,
    ) -> Result<&'a [u8], Failure> {
        meter.work(n as u64, self.cursor())?;
        let end = self
            .position
            .checked_add(n)
            .filter(|end| *end <= self.bytes.len())
            .ok_or_else(|| self.error(meter, FailureKind::Malformed, "declared_length"))?;
        let bytes = &self.bytes[self.position..end];
        self.position = end;
        Ok(bytes)
    }
    pub fn uint(&mut self, meter: &mut Meter<'_, impl MeterControl>) -> Result<u32, Failure> {
        let mut n = 0u32;
        for i in 0..5 {
            let b = self.byte(meter)?;
            if i == 4 && b & 0xf0 != 0 {
                return Err(self.error(meter, FailureKind::Malformed, "u32_leb_overflow"));
            }
            n |= ((b & 127) as u32) << (i * 7);
            if b & 128 == 0 {
                return Ok(n);
            }
        }
        Err(self.error(meter, FailureKind::Malformed, "u32_leb_unterminated"))
    }
    pub fn signed(
        &mut self,
        bits: u32,
        meter: &mut Meter<'_, impl MeterControl>,
    ) -> Result<i64, Failure> {
        let max = bits.div_ceil(7);
        let mut value = 0u64;
        for i in 0..max {
            let b = self.byte(meter)?;
            let p = b & 127;
            if i == max - 1 {
                let used = bits - 7 * i;
                let positive = (1u8 << (used - 1)) - 1;
                let negative = 127 ^ positive;
                if b & 128 != 0 || (p > positive && p < negative) {
                    return Err(self.error(meter, FailureKind::Malformed, "signed_leb_overflow"));
                }
            }
            value |= (p as u64).wrapping_shl(7 * i);
            if b & 128 == 0 {
                let shift = 7 * (i + 1);
                if shift < 64 && b & 64 != 0 {
                    value |= u64::MAX << shift;
                }
                return Ok(if bits == 32 {
                    value as i32 as i64
                } else {
                    value as i64
                });
            }
        }
        Err(self.error(meter, FailureKind::Malformed, "signed_leb_unterminated"))
    }
    pub fn count(
        &mut self,
        max: usize,
        meter: &mut Meter<'_, impl MeterControl>,
    ) -> Result<usize, Failure> {
        let n = self.uint(meter)? as usize;
        if n > max {
            Err(self
                .error(
                    meter,
                    FailureKind::ResourceExhausted,
                    "profile_vector_limit",
                )
                .resource(Resource::Profile, n as u64, max as u64))
        } else {
            Ok(n)
        }
    }
    pub fn ty(
        &mut self,
        floats: bool,
        meter: &mut Meter<'_, impl MeterControl>,
    ) -> Result<crate::Type, Failure> {
        match self.byte(meter)? {
            0x7f => Ok(crate::Type::I32),
            0x7e => Ok(crate::Type::I64),
            0x7d if floats => Ok(crate::Type::F32),
            0x7c if floats => Ok(crate::Type::F64),
            _ => Err(self.error(meter, FailureKind::Unsupported, "value_type")),
        }
    }
    pub fn end(&self, meter: &Meter<'_, impl MeterControl>) -> Result<(), Failure> {
        if self.position == self.bytes.len() {
            Ok(())
        } else {
            Err(self.error(meter, FailureKind::Malformed, "trailing_bytes"))
        }
    }
}
