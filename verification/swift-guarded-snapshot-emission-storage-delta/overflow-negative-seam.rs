
const NEGATIVE_OVERFLOW:u64=u64::MAX.checked_add(NET_DELTA).expect("deliberate checked delta overflow");
