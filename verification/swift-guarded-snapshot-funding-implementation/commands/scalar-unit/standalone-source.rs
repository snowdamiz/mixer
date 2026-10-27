// Standalone scalar harness. The synthetic F0 is not a measured Mixer floor.
mod recipe {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(366_896);
// Exact logical source-place recipe bound to the separately frozen owner
// correction. Every addition is const-evaluated; no runtime helper, local,
// iterable, allocation or second foundation is introduced by this recipe.
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.

pub fn check() {
assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,Some(445_136));
assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,Some(1_386_603));
assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,Some(if cfg!(test){1_467_930}else{1_386_603}));
assert_eq!(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1,430_175);
}
}
fn main(){
 recipe::check();
 let mut checks=0u64;
 for bits in [32u32,64u32] {
  let limit=(1u128<<bits)-1;
  for base in [0u128,1,300_000,400_000,366_896,limit-78_240,limit-78_239,limit] {
   for host in [false,true] {
    let common=base.checked_add(78_240).filter(|n|*n<=limit);
    let selected=common.and_then(|n|n.checked_add(941_467)).filter(|n|*n<=limit);
    let selected=if host{selected.and_then(|n|n.checked_add(81_327)).filter(|n|*n<=limit)}else{selected};
    let admitted=selected.and_then(|n|n.checked_add(430_175)).filter(|n|*n<=limit);
    let expected=base.checked_add(78_240+941_467+430_175+if host{81_327}else{0}).filter(|n|*n<=limit);
    assert_eq!(admitted,expected);checks+=1;
    if let Some(current)=selected {
     for grant in [0u128,300_000,400_000,current,current+430_174,current+430_175,limit] {
      let before=current;
      let preflight=current.checked_add(430_175).filter(|n|*n<=limit && *n<=grant);
      let after=preflight.unwrap_or(before);
      assert_eq!(after,if current+430_175<=limit && current+430_175<=grant {current+430_175}else{before});
      checks+=1;
     }
    }
   }
  }
 }
 assert!(usize::MAX.checked_add(1).is_none());
 assert!(u64::MAX.checked_add(1).is_none());
 println!("PASS {} scalar phase/overflow/refusal controls; no VM/writer",checks+2);
}
