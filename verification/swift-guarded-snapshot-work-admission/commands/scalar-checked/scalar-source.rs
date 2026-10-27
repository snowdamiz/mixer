const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
fn emission(b:u64,e:u64)->Option<u64>{
    19_537u64.checked_add(299_377u64.checked_mul(b)?)?.checked_add(32u64.checked_mul(e)?)
}
fn quote(b:u64,e:u64)->Option<u64>{
    SNAPSHOT_FIXED_EXECUTION_WORK_V1.checked_add(16_384)?.checked_add(emission(b,e)?)
}
fn main(){
    assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
    assert_eq!(451_703_621u64.checked_add(33_613).and_then(|n|n.checked_add(68_781))
        .and_then(|n|n.checked_add(7_155)).and_then(|n|n.checked_add(1_272)),Some(SNAPSHOT_FIXED_EXECUTION_WORK_V1));
    let mut checks=2;
    for b in [0u64,1,2,3,7,255,994,1_000_000,u64::MAX/299_377,u64::MAX/299_377+1,u64::MAX] {
      for e in [0u64,1,31,32,4096,1_000_000,u64::MAX/32,u64::MAX/32+1,u64::MAX] {
        let wide=451_814_442u128+16_384+19_537+299_377u128*u128::from(b)+32*u128::from(e);
        let expected=if wide<=u64::MAX as u128{Some(wide as u64)}else{None};
        assert_eq!(quote(b,e),expected); checks+=1;
        if let Some(price)=expected {
          for limit in [0u64,price.saturating_sub(1),price,price.saturating_add(1),1_000_000_000,u64::MAX] {
            assert_eq!(quote(b,e).filter(|n|*n<=limit).is_some(),wide<=u128::from(limit));checks+=1;
          }
        }
      }
    }
    assert!(quote(1,0).unwrap()<=1_000_000_000);checks+=1;
    assert!(quote(994,0).unwrap()<=1_000_000_000);checks+=1;
    assert!(quote(2_000,0).unwrap()>1_000_000_000);checks+=1;
    assert!(u64::MAX.checked_add(1_272).is_none());checks+=1;
    println!("{} checked arithmetic controls passed; synthetic integer geometry only",checks);
}
