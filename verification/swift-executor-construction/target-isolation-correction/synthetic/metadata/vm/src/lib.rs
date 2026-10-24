#[test]
fn product_marker() { assert_eq!(2 + 2, 4); }

#[cfg(test)]
mod experimental_swift_reactor {
    pub mod execution {
        #[test]
        fn frozen_construction_metadata() { assert_eq!(3 + 3, 6); }
    }
}
