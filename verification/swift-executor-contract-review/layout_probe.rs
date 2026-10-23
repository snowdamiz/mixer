#[test]
fn review_final_tail_named_layouts() {
    use crate::experimental_wasi::accounted::AccountedWasi;
    use crate::experimental_wasi::WasiUsage;
    use std::mem::align_of;
    macro_rules! emit {
        ($ty:ty) => { println!("{} {} {}", stringify!($ty), size_of::<$ty>(), align_of::<$ty>()); };
    }
    emit!(WasiUsage); emit!(Option<WasiUsage>);
    emit!(SwiftRunFailure); emit!(Option<SwiftRunFailure>); emit!(Result<(), SwiftRunFailure>);
    emit!(SwiftRunUsage); emit!(Option<SwiftRunUsage>);
    emit!(ReservationTicket); emit!(Option<ReservationTicket>);
    emit!(RuntimeControl); emit!(AdoptedProof); emit!(ValidatedSwiftReactor);
    emit!(Fault); emit!(Cursor); emit!(AccountedWasi);
    emit!(Option<&AccountedWasi>); emit!(&mut RuntimeControl);
    println!("foundation {}", foundation_construction_bytes().unwrap());
}
