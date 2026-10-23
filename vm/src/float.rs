//! Owned numeric-v2 semantics, derived from the WebAssembly numeric definitions.
//! Values carry IEEE bits; bitwise float instructions never canonicalize NaNs.
//! Arithmetic, rounding, square root and float-width conversions choose positive
//! canonical NaNs from the spec's permitted set, independently of host behavior.
use crate::{Error, Type, Value};

// Host rounding libraries can return a signaling NaN unchanged. Wasm arithmetic
// must return an arithmetic NaN (or a canonical NaN when all NaN inputs are
// canonical). Canonicalizing every NaN result satisfies both cases, including
// invalid operations with no NaN inputs. Use integer bits so this check itself
// cannot quiet or otherwise alter the value before classifying it.
// https://webassembly.github.io/spec/core/exec/numerics.html#nan-propagation
fn arithmetic_nan32(bits: u32) -> u32 {
    if bits & 0x7fff_ffff > 0x7f80_0000 {
        0x7fc0_0000
    } else {
        bits
    }
}
fn arithmetic_nan64(bits: u64) -> u64 {
    if bits & 0x7fff_ffff_ffff_ffff > 0x7ff0_0000_0000_0000 {
        0x7ff8_0000_0000_0000
    } else {
        bits
    }
}

pub(crate) fn shape(op: u8) -> Option<(Type, usize, Type)> {
    use Type::*;
    Some(match op {
        0x5b..=0x60 => (F32, 2, I32),
        0x61..=0x66 => (F64, 2, I32),
        0x8b..=0x91 => (F32, 1, F32),
        0x92..=0x98 => (F32, 2, F32),
        0x99..=0x9f => (F64, 1, F64),
        0xa0..=0xa6 => (F64, 2, F64),
        0xa8 | 0xa9 => (F32, 1, I32),
        0xaa | 0xab => (F64, 1, I32),
        0xae | 0xaf => (F32, 1, I64),
        0xb0 | 0xb1 => (F64, 1, I64),
        0xb2 | 0xb3 => (I32, 1, F32),
        0xb4 | 0xb5 => (I64, 1, F32),
        0xb6 => (F64, 1, F32),
        0xb7 | 0xb8 => (I32, 1, F64),
        0xb9 | 0xba => (I64, 1, F64),
        0xbb => (F32, 1, F64),
        0xbc => (F32, 1, I32),
        0xbd => (F64, 1, I64),
        0xbe => (I32, 1, F32),
        0xbf => (I64, 1, F64),
        _ => return None,
    })
}
pub(crate) fn saturating_shape(sub: u8) -> (Type, Type) {
    (
        if sub % 4 < 2 { Type::F32 } else { Type::F64 },
        if sub < 4 { Type::I32 } else { Type::I64 },
    )
}
fn pop32(s: &mut Vec<Value>) -> u32 {
    match s.pop().unwrap() {
        Value::F32(b) => b,
        _ => unreachable!("validated f32"),
    }
}
fn pop64(s: &mut Vec<Value>) -> u64 {
    match s.pop().unwrap() {
        Value::F64(b) => b,
        _ => unreachable!("validated f64"),
    }
}
fn integer(s: &mut Vec<Value>) -> Value {
    s.pop().unwrap()
}
fn truncated(x: f64, bits: u32, signed: bool, saturating: bool) -> Result<Value, &'static str> {
    if x.is_nan() {
        return if saturating {
            Ok(if bits == 32 {
                Value::I32(0)
            } else {
                Value::I64(0)
            })
        } else {
            Err("invalid_conversion_to_integer")
        };
    }
    let n = x.trunc();
    let value = match (bits, signed) {
        (32, true) => {
            if !saturating && (!(-2147483648.0..2147483648.0).contains(&n)) {
                return Err("integer_overflow");
            }
            Value::I32(n as i32)
        }
        (32, false) => {
            if !saturating && (!(0.0..4294967296.0).contains(&n)) {
                return Err("integer_overflow");
            }
            Value::I32(n as u32 as i32)
        }
        (64, true) => {
            if !saturating && (!(-9223372036854775808.0..9223372036854775808.0).contains(&n)) {
                return Err("integer_overflow");
            }
            Value::I64(n as i64)
        }
        (64, false) => {
            if !saturating && (!(0.0..18446744073709551616.0).contains(&n)) {
                return Err("integer_overflow");
            }
            Value::I64(n as u64 as i64)
        }
        _ => unreachable!(),
    };
    Ok(value)
}
pub(crate) fn saturating(sub: u8, s: &mut Vec<Value>) {
    let (input, output) = saturating_shape(sub);
    let x = if input == Type::F32 {
        f32::from_bits(pop32(s)) as f64
    } else {
        f64::from_bits(pop64(s))
    };
    s.push(
        truncated(
            x,
            if output == Type::I32 { 32 } else { 64 },
            sub.is_multiple_of(2),
            true,
        )
        .unwrap(),
    );
}
pub(crate) fn numeric(op: u8, s: &mut Vec<Value>) -> Result<(), &'static str> {
    use Value::*;
    match op {
        0x5b..=0x60 => {
            let b = f32::from_bits(pop32(s));
            let a = f32::from_bits(pop32(s));
            s.push(I32(match op {
                0x5b => a == b,
                0x5c => a != b,
                0x5d => a < b,
                0x5e => a > b,
                0x5f => a <= b,
                _ => a >= b,
            } as i32));
        }
        0x61..=0x66 => {
            let b = f64::from_bits(pop64(s));
            let a = f64::from_bits(pop64(s));
            s.push(I32(match op {
                0x61 => a == b,
                0x62 => a != b,
                0x63 => a < b,
                0x64 => a > b,
                0x65 => a <= b,
                _ => a >= b,
            } as i32));
        }
        0x8b..=0x98 => {
            let b = if op >= 0x92 { pop32(s) } else { 0 };
            let a = pop32(s);
            let x = f32::from_bits(a);
            let y = f32::from_bits(b);
            let bits = match op {
                0x8b => a & 0x7fff_ffff,
                0x8c => a ^ 0x8000_0000,
                0x8d => x.ceil().to_bits(),
                0x8e => x.floor().to_bits(),
                0x8f => x.trunc().to_bits(),
                0x90 => x.round_ties_even().to_bits(),
                0x91 => x.sqrt().to_bits(),
                0x92 => (x + y).to_bits(),
                0x93 => (x - y).to_bits(),
                0x94 => (x * y).to_bits(),
                0x95 => (x / y).to_bits(),
                0x96 => {
                    if x.is_nan() || y.is_nan() {
                        f32::NAN.to_bits()
                    } else if x == 0.0 && y == 0.0 {
                        a | b
                    } else {
                        if x < y { x } else { y }.to_bits()
                    }
                }
                0x97 => {
                    if x.is_nan() || y.is_nan() {
                        f32::NAN.to_bits()
                    } else if x == 0.0 && y == 0.0 {
                        a & b
                    } else {
                        if x > y { x } else { y }.to_bits()
                    }
                }
                0x98 => (a & 0x7fff_ffff) | (b & 0x8000_0000),
                _ => unreachable!(),
            };
            // abs, neg and copysign preserve the exact NaN payload bits.
            s.push(F32(if (0x8d..=0x97).contains(&op) {
                arithmetic_nan32(bits)
            } else {
                bits
            }));
        }
        0x99..=0xa6 => {
            let b = if op >= 0xa0 { pop64(s) } else { 0 };
            let a = pop64(s);
            let x = f64::from_bits(a);
            let y = f64::from_bits(b);
            let bits = match op {
                0x99 => a & 0x7fff_ffff_ffff_ffff,
                0x9a => a ^ 0x8000_0000_0000_0000,
                0x9b => x.ceil().to_bits(),
                0x9c => x.floor().to_bits(),
                0x9d => x.trunc().to_bits(),
                0x9e => x.round_ties_even().to_bits(),
                0x9f => x.sqrt().to_bits(),
                0xa0 => (x + y).to_bits(),
                0xa1 => (x - y).to_bits(),
                0xa2 => (x * y).to_bits(),
                0xa3 => (x / y).to_bits(),
                0xa4 => {
                    if x.is_nan() || y.is_nan() {
                        f64::NAN.to_bits()
                    } else if x == 0.0 && y == 0.0 {
                        a | b
                    } else {
                        if x < y { x } else { y }.to_bits()
                    }
                }
                0xa5 => {
                    if x.is_nan() || y.is_nan() {
                        f64::NAN.to_bits()
                    } else if x == 0.0 && y == 0.0 {
                        a & b
                    } else {
                        if x > y { x } else { y }.to_bits()
                    }
                }
                0xa6 => (a & 0x7fff_ffff_ffff_ffff) | (b & 0x8000_0000_0000_0000),
                _ => unreachable!(),
            };
            s.push(F64(if (0x9b..=0xa5).contains(&op) {
                arithmetic_nan64(bits)
            } else {
                bits
            }));
        }
        0xa8..=0xab | 0xae..=0xb1 => {
            let (input, _, output) = shape(op).unwrap();
            let x = if input == Type::F32 {
                f32::from_bits(pop32(s)) as f64
            } else {
                f64::from_bits(pop64(s))
            };
            s.push(truncated(
                x,
                if output == Type::I32 { 32 } else { 64 },
                op.is_multiple_of(2),
                false,
            )?);
        }
        0xb2..=0xb5 => {
            let x = match (op, integer(s)) {
                (0xb2, I32(x)) => x as f32,
                (0xb3, I32(x)) => x as u32 as f32,
                (0xb4, I64(x)) => x as f32,
                (0xb5, I64(x)) => x as u64 as f32,
                _ => unreachable!(),
            };
            s.push(F32(x.to_bits()));
        }
        0xb6 => {
            let x = f64::from_bits(pop64(s));
            s.push(F32(arithmetic_nan32((x as f32).to_bits())));
        }
        0xb7..=0xba => {
            let x = match (op, integer(s)) {
                (0xb7, I32(x)) => x as f64,
                (0xb8, I32(x)) => x as u32 as f64,
                (0xb9, I64(x)) => x as f64,
                (0xba, I64(x)) => x as u64 as f64,
                _ => unreachable!(),
            };
            s.push(F64(x.to_bits()));
        }
        0xbb => {
            let x = f32::from_bits(pop32(s));
            s.push(F64(arithmetic_nan64((x as f64).to_bits())));
        }
        0xbc => {
            let x = pop32(s);
            s.push(I32(x as i32));
        }
        0xbd => {
            let x = pop64(s);
            s.push(I64(x as i64));
        }
        0xbe => {
            let I32(x) = integer(s) else { unreachable!() };
            s.push(F32(x as u32));
        }
        0xbf => {
            let I64(x) = integer(s) else { unreachable!() };
            s.push(F64(x as u64));
        }
        _ => unreachable!("validated numeric-v2 opcode"),
    }
    Ok(())
}

// Read control state before performing arithmetic: even a diagnostic subnormal
// probe could otherwise raise a hardware trap when the host enabled FP traps.
fn control_state_supported() -> bool {
    #[cfg(target_arch = "aarch64")]
    {
        let control: u64;
        // SAFETY: reads the calling thread's FPCR into a register, touches no
        // memory and changes no state. Only default-NaN mode may differ from
        // zero; canonical NaNs are valid Wasm results. Unknown control modes,
        // trap enables, rounding changes and flush modes all fail closed.
        unsafe {
            core::arch::asm!("mrs {control}, fpcr",control=out(reg)control,options(nomem,nostack,preserves_flags));
        }
        return control & !0x0200_0000 == 0;
    }
    #[cfg(target_arch = "x86_64")]
    {
        let mut sse = 0u32;
        let mut x87 = 0u16;
        // SAFETY: stores CPU control words into correctly sized, aligned local
        // variables; no FP state is modified. Non-waiting fnstcw cannot raise
        // an already pending x87 exception.
        unsafe {
            core::arch::asm!("stmxcsr [{pointer}]",pointer=in(reg)&mut sse,options(nostack,preserves_flags));
            core::arch::asm!("fnstcw [{pointer}]",pointer=in(reg)&mut x87,options(nostack,preserves_flags));
        }
        return sse & !0x3f == 0x1f80 && x87 & 0x0c3f == 0x003f;
    }
    #[allow(unreachable_code)]
    false
}

/// Numeric-v2 requires the platform's default nearest-even IEEE environment.
/// Reject a changed rounding mode/flush-to-zero environment instead of silently
/// running Wasm with different arithmetic. No host FP control state is modified; arithmetic probes may set normal
/// sticky exception flags.
pub(crate) fn environment() -> Result<(), Error> {
    #[cfg(any(target_vendor = "apple", target_os = "linux", target_os = "android"))]
    {
        #[cfg_attr(not(target_vendor = "apple"), link(name = "m"))]
        unsafe extern "C" {
            fn fegetround() -> std::ffi::c_int;
        }
        // SAFETY: POSIX/platform fegetround takes no pointers and only reads the
        // calling thread's floating environment. FE_TONEAREST is zero on these
        // explicitly supported platform families, verified by platform headers.
        let nearest = unsafe { fegetround() } == 0;
        if !nearest || !control_state_supported() {
            return Err(Error::new("unsupported_float_environment","numeric-v2 requires masked FP exceptions, nearest-even rounding and gradual underflow",None,0));
        }
        let tiny32 = std::hint::black_box(f32::from_bits(1)) * std::hint::black_box(1.0f32);
        let tiny64 = std::hint::black_box(f64::from_bits(1)) * std::hint::black_box(1.0f64);
        if tiny32.to_bits() == 1 && tiny64.to_bits() == 1 {
            return Ok(());
        }
    }
    Err(Error::new(
        "unsupported_float_environment",
        "numeric-v2 requires nearest-even rounding and gradual underflow on a qualified host",
        None,
        0,
    ))
}
