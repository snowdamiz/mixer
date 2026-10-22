//! Non-authorizing structural inventory; accepting an immediate shape here does
//! not add that opcode to the executable profile. Strict validation is separate.
use crate::{decode::Reader, validation_inventory, Error, Inventory, Limits};
pub const INVENTORY_BYTES: usize = 128 * 1024 * 1024;
pub fn inventory(bytes: &[u8], limits: &Limits) -> Inventory {
    let validation = validation_inventory(bytes, limits);
    let mut inv = Inventory {
        error: validation.error,
        ..Default::default()
    };
    if let Err(e) = scan(bytes, &mut inv) {
        inv.inventory_error = Some(e);
    } else {
        inv.complete = true;
    }
    inv
}
fn scan(bytes: &[u8], inv: &mut Inventory) -> Result<(), Error> {
    if bytes.len() > INVENTORY_BYTES {
        return Err(Error::new(
            "limit",
            "inspection byte ceiling is 128MiB",
            None,
            0,
        ));
    }
    let mut r = Reader::at(bytes, 0);
    if r.take(8)? != b"\0asm\x01\0\0\0" {
        return Err(r.err("malformed", "expected Wasm version 1"));
    }
    let mut imports = 0u32;
    let mut total = 0usize;
    while r.pos < r.bytes.len() {
        let id = r.byte()?;
        let size = r.u32()? as usize;
        let base = r.offset();
        let data = r.take(size)?;
        let mut s = Reader::at(data, base);
        match id {
            2 => {
                for _ in 0..s.count(100_000)? {
                    let module = s.name()?;
                    let name = s.name()?;
                    let kind = s.byte()?;
                    if kind != 0 {
                        return Err(s.err(
                            "inventory_unsupported",
                            "inventory only describes function imports",
                        ));
                    }
                    let index = s.u32()?;
                    inv.imports.push((module, name, index));
                    imports += 1;
                }
                s.end()?;
            }
            7 => {
                for _ in 0..s.count(100_000)? {
                    let name = s.name()?;
                    let kind = s.byte()?;
                    let index = s.u32()?;
                    inv.exports.push((name, kind, index));
                }
                s.end()?;
            }
            10 => {
                for function in 0..s.count(100_000)? {
                    let size = s.u32()? as usize;
                    let base = s.offset();
                    let data = s.take(size)?;
                    let mut b = Reader::at(data, base);
                    b.function = Some(imports + function as u32);
                    for _ in 0..b.count(100_000)? {
                        b.u32()?;
                        match b.byte()? {
                            0x7f | 0x7e | 0x7d | 0x7c | 0x7b | 0x70 | 0x6f => {}
                            _ => {
                                return Err(
                                    b.err("inventory_unsupported", "unknown local type encoding")
                                )
                            }
                        }
                    }
                    while b.pos < b.bytes.len() {
                        total += 1;
                        if total > 16_000_000 {
                            return Err(b.err("limit", "inspection instruction ceiling exceeded"));
                        }
                        let offset = b.offset();
                        let op = b.byte()?;
                        *inv.opcodes.entry(op).or_default() += 1;
                        match op{
                    0x00|0x01|0x05|0x0b|0x0f|0x1a|0x1b|0x45..=0xc4|0xd1|0xd3=>{},
                    0x02..=0x04=>{b.signed(33)?;},
                    0x0c|0x0d|0x10|0x12|0x14|0x15|0x20..=0x26|0xd2|0xd4|0xd5=>{b.u32()?;},
                    0x0e=>{for _ in 0..b.count(1_000_000)?{b.u32()?;}b.u32()?;},
                    0x11|0x13=>{b.u32()?;b.u32()?;},
                    0x1c=>{for _ in 0..b.count(4096)?{b.byte()?;}},
                    0x28..=0x3e=>{b.u32()?;b.u32()?;},0x3f|0x40=>{b.u32()?;},
                    0x41=>{b.signed(32)?;},0x42=>{b.signed(64)?;},0x43=>{b.take(4)?;},0x44=>{b.take(8)?;},0xd0=>{b.signed(33)?;},
                    0xfc=>{let sub=b.u32()?;*inv.extended_opcodes.entry(format!("0xfc:{sub}")).or_default()+=1;match sub{0..=7=>{},8|10|12|14=>{b.u32()?;b.u32()?;},9|11|13|15..=17=>{b.u32()?;},_=>return Err(b.err("inventory_unsupported","unknown 0xfc immediate shape"))}},
                    _=>return Err(Error::new("inventory_unsupported",format!("unknown immediate shape for opcode 0x{op:02x}; inventory is partial"),b.function,offset)),
                }
                    }
                }
                s.end()?;
            }
            _ => {}
        }
    }
    Ok(())
}
